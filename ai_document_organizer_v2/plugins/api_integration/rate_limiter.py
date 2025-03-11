"""
Rate Limiter for External API Integration Framework.

This module provides intelligent throttling for API requests to avoid
hitting rate limits imposed by external API services.
"""

import logging
import time
import threading
from typing import Any, Dict, List, Optional, Union, Set
from collections import deque


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Intelligent rate limiter for API requests.
    
    This class manages request rate limiting based on configurable rules,
    tracking request history, and enforcing limits to avoid API throttling.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Rate Limiter.
        
        Args:
            config: Optional configuration dictionary for the limiter
        """
        self.config = config or {}
        
        # API registry with rate limit rules
        self.api_registry = {}  # type: Dict[str, Dict[str, Any]]
        
        # Request history tracking
        self.request_history = {}  # type: Dict[str, deque]
        
        # Active requests tracking
        self.active_requests = {}  # type: Dict[str, int]
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Rate Limiter initialized")
    
    def register_api(self, api_name: str, rules: Dict[str, Any]) -> bool:
        """
        Register an API with rate limit rules.
        
        Args:
            api_name: Name of the API
            rules: Dictionary with rate limit rules:
                - requests_per_second: Maximum requests per second
                - requests_per_minute: Maximum requests per minute
                - requests_per_hour: Maximum requests per hour
                - requests_per_day: Maximum requests per day
                - concurrent_requests: Maximum concurrent requests
                
        Returns:
            True if registration was successful, False otherwise
        """
        with self._lock:
            # Register the API
            self.api_registry[api_name] = rules
            
            # Initialize request history tracking
            self.request_history[api_name] = deque(maxlen=10000)  # Limit history size
            
            # Initialize active requests tracking
            self.active_requests[api_name] = 0
            
            logger.info(f"Registered API {api_name} with rate limit rules: {rules}")
            return True
    
    def unregister_api(self, api_name: str) -> bool:
        """
        Unregister an API and remove its rate limit rules.
        
        Args:
            api_name: Name of the API to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        with self._lock:
            if api_name not in self.api_registry:
                logger.warning(f"API {api_name} is not registered")
                return False
                
            # Remove from registry
            del self.api_registry[api_name]
            
            # Clean up request history
            if api_name in self.request_history:
                del self.request_history[api_name]
                
            # Clean up active requests
            if api_name in self.active_requests:
                del self.active_requests[api_name]
                
            logger.info(f"Unregistered API {api_name}")
            return True
    
    def record_request(self, api_name: str) -> bool:
        """
        Record an API request.
        
        Args:
            api_name: Name of the API
            
        Returns:
            True if recording was successful, False otherwise
        """
        with self._lock:
            if api_name not in self.api_registry:
                logger.warning(f"API {api_name} is not registered")
                return False
                
            # Record request timestamp
            self.request_history[api_name].append(time.time())
            
            # Update active requests count
            self.active_requests[api_name] = max(0, self.active_requests[api_name] - 1)
            
            return True
    
    def record_request_start(self, api_name: str) -> bool:
        """
        Record the start of an API request.
        
        Args:
            api_name: Name of the API
            
        Returns:
            True if recording was successful, False otherwise
        """
        with self._lock:
            if api_name not in self.api_registry:
                logger.warning(f"API {api_name} is not registered")
                return False
                
            # Increment active requests count
            self.active_requests[api_name] += 1
            
            return True
    
    def can_make_request(self, api_name: str) -> bool:
        """
        Check if a request can be made based on rate limit rules.
        
        Args:
            api_name: Name of the API
            
        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            if api_name not in self.api_registry:
                logger.warning(f"API {api_name} is not registered")
                return True  # Allow requests for unregistered APIs
                
            # Get rate limit rules
            rules = self.api_registry[api_name]
            
            # Check concurrent requests limit
            concurrent_limit = rules.get('concurrent_requests')
            if concurrent_limit is not None:
                active = self.active_requests.get(api_name, 0)
                if active >= concurrent_limit:
                    logger.warning(f"Concurrent request limit ({concurrent_limit}) reached for {api_name}")
                    return False
            
            # Get request history
            history = self.request_history.get(api_name, deque())
            if not history:
                # No history, allow request
                return True
                
            # Current time
            now = time.time()
            
            # Check requests_per_second limit
            rps_limit = rules.get('requests_per_second')
            if rps_limit is not None:
                # Count requests in the last second
                second_ago = now - 1
                requests_last_second = sum(1 for ts in history if ts >= second_ago)
                
                if requests_last_second >= rps_limit:
                    logger.warning(f"Rate limit ({rps_limit} per second) reached for {api_name}")
                    return False
            
            # Check requests_per_minute limit
            rpm_limit = rules.get('requests_per_minute')
            if rpm_limit is not None:
                # Count requests in the last minute
                minute_ago = now - 60
                requests_last_minute = sum(1 for ts in history if ts >= minute_ago)
                
                if requests_last_minute >= rpm_limit:
                    logger.warning(f"Rate limit ({rpm_limit} per minute) reached for {api_name}")
                    return False
            
            # Check requests_per_hour limit
            rph_limit = rules.get('requests_per_hour')
            if rph_limit is not None:
                # Count requests in the last hour
                hour_ago = now - 3600
                requests_last_hour = sum(1 for ts in history if ts >= hour_ago)
                
                if requests_last_hour >= rph_limit:
                    logger.warning(f"Rate limit ({rph_limit} per hour) reached for {api_name}")
                    return False
            
            # Check requests_per_day limit
            rpd_limit = rules.get('requests_per_day')
            if rpd_limit is not None:
                # Count requests in the last day
                day_ago = now - 86400
                requests_last_day = sum(1 for ts in history if ts >= day_ago)
                
                if requests_last_day >= rpd_limit:
                    logger.warning(f"Rate limit ({rpd_limit} per day) reached for {api_name}")
                    return False
            
            # All checks passed, allow request
            return True
    
    def get_wait_time(self, api_name: str) -> float:
        """
        Get the waiting time until the next request can be made.
        
        Args:
            api_name: Name of the API
            
        Returns:
            Waiting time in seconds
        """
        with self._lock:
            if api_name not in self.api_registry:
                logger.warning(f"API {api_name} is not registered")
                return 0.0  # No waiting time for unregistered APIs
                
            # Get rate limit rules
            rules = self.api_registry[api_name]
            
            # Get request history
            history = self.request_history.get(api_name, deque())
            if not history:
                # No history, no waiting time
                return 0.0
                
            # Current time
            now = time.time()
            
            # Check concurrent requests limit
            concurrent_limit = rules.get('concurrent_requests')
            if concurrent_limit is not None:
                active = self.active_requests.get(api_name, 0)
                if active >= concurrent_limit:
                    # Estimate wait time based on average request duration
                    durations = []
                    last_request = None
                    for ts in history:
                        if last_request is not None:
                            durations.append(ts - last_request)
                        last_request = ts
                    
                    avg_duration = sum(durations) / len(durations) if durations else 1.0
                    return avg_duration
            
            # Calculate waiting time for each rate limit rule
            wait_times = []
            
            # Check requests_per_second limit
            rps_limit = rules.get('requests_per_second')
            if rps_limit is not None:
                # Get timestamps in the last second
                second_ago = now - 1
                recent_requests = sorted([ts for ts in history if ts >= second_ago])
                
                if len(recent_requests) >= rps_limit and recent_requests:
                    # Calculate time until oldest request is outside the window
                    wait_time = second_ago + 1 - recent_requests[-(rps_limit):][-1]
                    wait_times.append(max(0.0, wait_time))
            
            # Check requests_per_minute limit
            rpm_limit = rules.get('requests_per_minute')
            if rpm_limit is not None:
                # Get timestamps in the last minute
                minute_ago = now - 60
                recent_requests = sorted([ts for ts in history if ts >= minute_ago])
                
                if len(recent_requests) >= rpm_limit and recent_requests:
                    # Calculate time until oldest request is outside the window
                    wait_time = minute_ago + 60 - recent_requests[-(rpm_limit):][-1]
                    wait_times.append(max(0.0, wait_time))
            
            # Check requests_per_hour limit
            rph_limit = rules.get('requests_per_hour')
            if rph_limit is not None:
                # Get timestamps in the last hour
                hour_ago = now - 3600
                recent_requests = sorted([ts for ts in history if ts >= hour_ago])
                
                if len(recent_requests) >= rph_limit and recent_requests:
                    # Calculate time until oldest request is outside the window
                    wait_time = hour_ago + 3600 - recent_requests[-(rph_limit):][-1]
                    wait_times.append(max(0.0, wait_time))
            
            # Check requests_per_day limit
            rpd_limit = rules.get('requests_per_day')
            if rpd_limit is not None:
                # Get timestamps in the last day
                day_ago = now - 86400
                recent_requests = sorted([ts for ts in history if ts >= day_ago])
                
                if len(recent_requests) >= rpd_limit and recent_requests:
                    # Calculate time until oldest request is outside the window
                    wait_time = day_ago + 86400 - recent_requests[-(rpd_limit):][-1]
                    wait_times.append(max(0.0, wait_time))
            
            # Return the maximum waiting time among all rate limit rules
            return max(wait_times) if wait_times else 0.0
    
    def get_exponential_backoff_time(self, api_name: str, attempt: int) -> float:
        """
        Get exponential backoff time for retrying requests.
        
        Args:
            api_name: Name of the API
            attempt: Current attempt number (starting from 1)
            
        Returns:
            Exponential backoff time in seconds
        """
        if attempt <= 0:
            return 0.0
            
        # Base delay in seconds
        base_delay = self.config.get('base_delay', 1.0)
        
        # Maximum delay in seconds
        max_delay = self.config.get('max_delay', 60.0)
        
        # Calculate exponential backoff time with jitter
        jitter = 0.1 * (2 ** (attempt - 1))  # 10% jitter
        backoff_time = min(max_delay, base_delay * (2 ** (attempt - 1))) * (1.0 + jitter)
        
        return backoff_time
    
    def get_api_stats(self, api_name: str) -> Dict[str, Any]:
        """
        Get statistics for an API.
        
        Args:
            api_name: Name of the API
            
        Returns:
            Dictionary with API statistics
        """
        with self._lock:
            if api_name not in self.api_registry:
                return {
                    'api_name': api_name,
                    'registered': False
                }
                
            # Get rate limit rules
            rules = self.api_registry[api_name]
            
            # Get request history
            history = self.request_history.get(api_name, deque())
            
            # Calculate statistics
            now = time.time()
            stats = {
                'api_name': api_name,
                'registered': True,
                'rules': rules,
                'active_requests': self.active_requests.get(api_name, 0),
                'total_requests': len(history),
                'can_make_request': self.can_make_request(api_name),
                'wait_time': self.get_wait_time(api_name)
            }
            
            # Calculate requests in different time windows
            second_ago = now - 1
            minute_ago = now - 60
            hour_ago = now - 3600
            day_ago = now - 86400
            
            stats['requests_last_second'] = sum(1 for ts in history if ts >= second_ago)
            stats['requests_last_minute'] = sum(1 for ts in history if ts >= minute_ago)
            stats['requests_last_hour'] = sum(1 for ts in history if ts >= hour_ago)
            stats['requests_last_day'] = sum(1 for ts in history if ts >= day_ago)
            
            # Calculate request rates
            stats['requests_per_second'] = stats['requests_last_second'] / 1.0
            stats['requests_per_minute'] = stats['requests_last_minute'] / 60.0
            stats['requests_per_hour'] = stats['requests_last_hour'] / 3600.0
            stats['requests_per_day'] = stats['requests_last_day'] / 86400.0
            
            return stats
    
    def clear_history(self, api_name: str) -> bool:
        """
        Clear request history for an API.
        
        Args:
            api_name: Name of the API
            
        Returns:
            True if clearing was successful, False otherwise
        """
        with self._lock:
            if api_name not in self.api_registry:
                logger.warning(f"API {api_name} is not registered")
                return False
                
            # Clear request history
            if api_name in self.request_history:
                self.request_history[api_name].clear()
                
            # Reset active requests
            if api_name in self.active_requests:
                self.active_requests[api_name] = 0
                
            logger.info(f"Cleared request history for {api_name}")
            return True
    
    def update_rules(self, api_name: str, rules: Dict[str, Any]) -> bool:
        """
        Update rate limit rules for an API.
        
        Args:
            api_name: Name of the API
            rules: Dictionary with new rate limit rules
            
        Returns:
            True if update was successful, False otherwise
        """
        with self._lock:
            if api_name not in self.api_registry:
                logger.warning(f"API {api_name} is not registered")
                return False
                
            # Update rules
            self.api_registry[api_name].update(rules)
            
            logger.info(f"Updated rate limit rules for {api_name}: {rules}")
            return True