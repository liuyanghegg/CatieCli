"""
Enhanced logging system for WenXiaoBai API proxy service.
Provides comprehensive logging for incoming requests and API calls.
"""
import json
import time
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import logging


@dataclass
class LogEntry:
    """Structure for log entries with correlation support."""
    timestamp: datetime
    level: str  # INFO, DEBUG, ERROR, WARNING
    component: str  # REQUEST, API, SESSION, ERROR
    message: str
    details: Dict[str, Any]
    request_id: str  # For correlation


@dataclass
class RequestLogData:
    """Structure for request log data."""
    method: str
    endpoint: str
    client_ip: str
    headers: Dict[str, str]
    body: Dict[str, Any]
    timestamp: datetime
    request_id: str


class RequestLogger:
    """
    Logger for incoming HTTP requests with detailed information capture.
    Handles request logging, parameter logging, and timing information.
    """
    
    def __init__(self, logger_name: str = "RequestLogger"):
        """Initialize the request logger."""
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Create console handler if not already exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Sensitive headers to exclude from logging
        self.sensitive_headers = {
            'authorization', 'x-yuanshi-authorization', 'cookie', 
            'x-api-key', 'api-key', 'secret-key', 'access-token'
        }
        
        # Sensitive body fields to exclude from logging
        self.sensitive_body_fields = {
            'password', 'secret', 'token', 'key', 'credential',
            'secret_key', 'access_token', 'api_key'
        }
    
    def log_incoming_request(self, request, endpoint: str, client_ip: str) -> str:
        """
        Log incoming HTTP request with method, endpoint, client IP, and timestamp.
        
        Args:
            request: Flask request object
            endpoint: The endpoint being accessed
            client_ip: Client IP address
            
        Returns:
            str: Generated request ID for correlation
        """
        request_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        log_data = RequestLogData(
            method=request.method,
            endpoint=endpoint,
            client_ip=client_ip,
            headers=self._filter_sensitive_headers(dict(request.headers)),
            body={},  # Will be populated by log_request_parameters
            timestamp=timestamp,
            request_id=request_id
        )
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level="INFO",
            component="REQUEST",
            message=f"Incoming {request.method} request to {endpoint}",
            details={
                "method": request.method,
                "endpoint": endpoint,
                "client_ip": client_ip,
                "user_agent": request.headers.get('User-Agent', 'Unknown'),
                "content_type": request.headers.get('Content-Type', 'Unknown')
            },
            request_id=request_id
        )
        
        self.logger.info(
            f"[{request_id}] {log_entry.message} - "
            f"IP: {client_ip}, Method: {request.method}, "
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:50]}..."
        )
        
        return request_id
    
    def log_request_parameters(self, data: Dict[str, Any], headers: Dict[str, str], request_id: str):
        """
        Log request headers and body parameters, excluding sensitive data.
        
        Args:
            data: Request body data
            headers: Request headers
            request_id: Request correlation ID
        """
        filtered_headers = self._filter_sensitive_headers(headers)
        filtered_body = self._filter_sensitive_body(data)
        
        log_entry = LogEntry(
            timestamp=datetime.now(),
            level="DEBUG",
            component="REQUEST",
            message="Request parameters logged",
            details={
                "headers_count": len(filtered_headers),
                "body_keys": list(filtered_body.keys()) if isinstance(filtered_body, dict) else "non-dict",
                "content_length": len(json.dumps(filtered_body)) if filtered_body else 0
            },
            request_id=request_id
        )
        
        self.logger.debug(
            f"[{request_id}] Request parameters - "
            f"Headers: {len(filtered_headers)} items, "
            f"Body keys: {list(filtered_body.keys()) if isinstance(filtered_body, dict) else 'N/A'}, "
            f"Content size: {len(json.dumps(filtered_body)) if filtered_body else 0} bytes"
        )
        
        # Log detailed parameters in debug mode
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"[{request_id}] Headers: {json.dumps(filtered_headers, indent=2)}")
            self.logger.debug(f"[{request_id}] Body: {json.dumps(filtered_body, indent=2)}")
    
    def log_request_timing(self, start_time: float, end_time: float, request_id: str):
        """
        Log request processing timing for performance monitoring.
        
        Args:
            start_time: Request start timestamp
            end_time: Request end timestamp
            request_id: Request correlation ID
        """
        duration = end_time - start_time
        duration_ms = duration * 1000
        
        log_entry = LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            component="REQUEST",
            message="Request timing recorded",
            details={
                "duration_seconds": duration,
                "duration_ms": duration_ms,
                "start_time": start_time,
                "end_time": end_time
            },
            request_id=request_id
        )
        
        # Determine log level based on duration
        if duration_ms > 5000:  # > 5 seconds
            level = "WARNING"
            message = f"SLOW REQUEST [{request_id}] Duration: {duration_ms:.2f}ms"
        elif duration_ms > 1000:  # > 1 second
            level = "INFO"
            message = f"[{request_id}] Request completed in {duration_ms:.2f}ms"
        else:
            level = "DEBUG"
            message = f"[{request_id}] Request completed in {duration_ms:.2f}ms"
        
        getattr(self.logger, level.lower())(message)
    
    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Filter out sensitive headers from logging.
        
        Args:
            headers: Original headers dictionary
            
        Returns:
            Dict[str, str]: Filtered headers with sensitive data masked
        """
        filtered = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in self.sensitive_headers:
                # Mask sensitive headers but show partial info for debugging
                if len(value) > 10:
                    filtered[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    filtered[key] = "***MASKED***"
            else:
                filtered[key] = value
        return filtered
    
    def _filter_sensitive_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out sensitive body fields from logging.
        
        Args:
            body: Original body data
            
        Returns:
            Dict[str, Any]: Filtered body with sensitive data masked
        """
        if not isinstance(body, dict):
            return body
        
        filtered = {}
        for key, value in body.items():
            key_lower = key.lower()
            if key_lower in self.sensitive_body_fields:
                filtered[key] = "***MASKED***"
            elif isinstance(value, dict):
                # Recursively filter nested dictionaries
                filtered[key] = self._filter_sensitive_body(value)
            elif isinstance(value, list):
                # Filter lists that might contain dictionaries
                filtered[key] = [
                    self._filter_sensitive_body(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value
        return filtered


@dataclass
class APICallLogData:
    """Structure for API call log data."""
    model: str
    query: str
    conversation_id: Optional[str]
    turn_index: int
    abilities: List[Dict[str, Any]]
    request_headers: Dict[str, str]
    response_status: int
    response_headers: Dict[str, str]
    timing: float
    request_id: str


class APIDebugLogger:
    """
    Logger for API calls to WenXiaoBai with detailed debugging information.
    Handles API parameter logging, response logging, and error logging.
    """
    
    def __init__(self, logger_name: str = "APIDebugLogger"):
        """Initialize the API debug logger."""
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Create console handler if not already exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Sensitive authentication fields to mask
        self.sensitive_auth_fields = {
            'secret_key', 'access_token', 'api_key', 'password', 
            'authorization', 'x-yuanshi-authorization', 'signature'
        }
    
    def log_api_call_parameters(self, model: str, query: str, conversation_id: Optional[str] = None, 
                               abilities: List[Dict[str, Any]] = None, request_id: str = None, 
                               **kwargs) -> str:
        """
        Log API call parameters including model, query, and conversation context.
        
        Args:
            model: Model name being used
            query: User query being sent
            conversation_id: Conversation ID if continuing a conversation
            abilities: List of model abilities/capabilities
            request_id: Request correlation ID
            **kwargs: Additional parameters
            
        Returns:
            str: Generated API call ID for correlation
        """
        api_call_id = request_id or str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Truncate query for logging (first 100 chars)
        query_preview = query[:100] + "..." if len(query) > 100 else query
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level="INFO",
            component="API",
            message="API call parameters logged",
            details={
                "model": model,
                "query_length": len(query),
                "query_preview": query_preview,
                "conversation_id": conversation_id,
                "abilities_count": len(abilities) if abilities else 0,
                "abilities": abilities or [],
                "additional_params": list(kwargs.keys())
            },
            request_id=api_call_id
        )
        
        self.logger.info(
            f"[{api_call_id}] API Call - Model: {model}, "
            f"Query: '{query_preview}', "
            f"ConvID: {conversation_id or 'new'}, "
            f"Abilities: {len(abilities) if abilities else 0}"
        )
        
        # Log detailed parameters in debug mode
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"[{api_call_id}] Full query: {query}")
            self.logger.debug(f"[{api_call_id}] Abilities: {json.dumps(abilities, indent=2)}")
            if kwargs:
                self.logger.debug(f"[{api_call_id}] Additional params: {json.dumps(kwargs, indent=2)}")
        
        return api_call_id
    
    def log_api_response(self, status_code: int, headers: Dict[str, str], 
                        response_preview: str = None, request_id: str = None, 
                        timing: float = None):
        """
        Log API response status, headers, and initial response data.
        
        Args:
            status_code: HTTP status code from API response
            headers: Response headers
            response_preview: Preview of response content (first few lines)
            request_id: Request correlation ID
            timing: Response time in seconds
        """
        api_call_id = request_id or str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Filter sensitive headers
        filtered_headers = self._filter_sensitive_headers(headers)
        
        # Truncate response preview
        if response_preview and len(response_preview) > 200:
            response_preview = response_preview[:200] + "..."
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level="INFO" if 200 <= status_code < 300 else "WARNING",
            component="API",
            message="API response received",
            details={
                "status_code": status_code,
                "headers_count": len(filtered_headers),
                "response_preview_length": len(response_preview) if response_preview else 0,
                "timing_seconds": timing
            },
            request_id=api_call_id
        )
        
        timing_info = f", Time: {timing:.3f}s" if timing else ""
        
        # Use appropriate log level based on status code
        log_level = "INFO" if 200 <= status_code < 300 else "WARNING"
        log_method = getattr(self.logger, log_level.lower())
        
        log_method(
            f"[{api_call_id}] API Response - Status: {status_code}, "
            f"Headers: {len(filtered_headers)} items{timing_info}"
        )
        
        if response_preview:
            self.logger.debug(f"[{api_call_id}] Response preview: {response_preview}")
        
        # Log detailed headers in debug mode
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"[{api_call_id}] Response headers: {json.dumps(filtered_headers, indent=2)}")
    
    def log_api_error(self, error_details: str, status_code: int = None, 
                     request_id: str = None, exception: Exception = None):
        """
        Log detailed API error information for debugging.
        
        Args:
            error_details: Error message or details
            status_code: HTTP status code if available
            request_id: Request correlation ID
            exception: Exception object if available
        """
        api_call_id = request_id or str(uuid.uuid4())
        timestamp = datetime.now()
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level="ERROR",
            component="API",
            message="API error occurred",
            details={
                "error_details": error_details,
                "status_code": status_code,
                "exception_type": type(exception).__name__ if exception else None,
                "exception_message": str(exception) if exception else None
            },
            request_id=api_call_id
        )
        
        error_msg = f"[{api_call_id}] API Error - {error_details}"
        if status_code:
            error_msg += f" (Status: {status_code})"
        if exception:
            error_msg += f" - {type(exception).__name__}: {str(exception)}"
        
        self.logger.error(error_msg)
        
        # Log stack trace in debug mode
        if exception and self.logger.isEnabledFor(logging.DEBUG):
            import traceback
            self.logger.debug(f"[{api_call_id}] Stack trace: {traceback.format_exc()}")
    
    def log_authentication_info(self, username: str = None, device_id: str = None, 
                               request_id: str = None, **auth_params):
        """
        Log authentication parameters excluding sensitive keys.
        
        Args:
            username: Username for authentication
            device_id: Device ID for authentication
            request_id: Request correlation ID
            **auth_params: Additional authentication parameters
        """
        api_call_id = request_id or str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Filter sensitive authentication data
        filtered_auth = self._filter_sensitive_auth(auth_params)
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level="DEBUG",
            component="API",
            message="Authentication info logged",
            details={
                "username": username,
                "device_id": device_id[:8] + "..." if device_id and len(device_id) > 8 else device_id,
                "auth_params": list(filtered_auth.keys())
            },
            request_id=api_call_id
        )
        
        device_preview = device_id[:8] + "..." if device_id and len(device_id) > 8 else device_id
        
        self.logger.debug(
            f"[{api_call_id}] Auth Info - User: {username}, "
            f"Device: {device_preview}, "
            f"Params: {list(filtered_auth.keys())}"
        )
    
    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Filter out sensitive headers from logging.
        
        Args:
            headers: Original headers dictionary
            
        Returns:
            Dict[str, str]: Filtered headers with sensitive data masked
        """
        filtered = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.sensitive_auth_fields):
                # Mask sensitive headers but show partial info for debugging
                if len(value) > 10:
                    filtered[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    filtered[key] = "***MASKED***"
            else:
                filtered[key] = value
        return filtered
    
    def _filter_sensitive_auth(self, auth_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out sensitive authentication parameters from logging.
        
        Args:
            auth_params: Original authentication parameters
            
        Returns:
            Dict[str, Any]: Filtered parameters with sensitive data masked
        """
        filtered = {}
        for key, value in auth_params.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.sensitive_auth_fields):
                filtered[key] = "***MASKED***"
            else:
                filtered[key] = value
        return filtered