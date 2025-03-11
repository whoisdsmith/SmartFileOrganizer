"""
Rate Limiter for the External API Integration Framework.

This module provides rate limiting capabilities for API calls to prevent
reaching API rate limits and ensure proper throttling of requests.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from collections import deque


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Implements rate limiting for API requests.
    
    This class tracks API requests and enforces rate limits based on configured rules,
    helping to prevent reaching API rate limits and ensuring proper throttling.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the rate limiter with configuration.
        
        Args:
            config: Configuration dictionary with rate limit rules
                   Example: {
                       'requests_per_minute': 60,
                       'requests_per_hour': 1000,
                       'requests_per_day': 10000,
                       'concurrent_requests': 5
                   }
        """
        self.config = config or {}
        self.lock = threading.RLock()
        
        # Default rate limits if not specified
        self.requests_per_minute = self.config.get('requests_per_minute', 60)
        self.requests_per_hour = self.config.get('requests_per_hour', 1000)
        self.requests_per_day = self.config.get('requests_per_day', 10000)
        self.concurrent_requests = self.config.get('concurrent_requests', 5)
        
        # Track request history
        self.request_history = deque(maxlen=max(self.requests_per_day, 10000))
        
        # Tracking concurrent requests
        self.active_requests = 0
        
        # Track when the rate limits will reset
        self.minute_reset_time = time.time() + 60
        self.hour_reset_time = time.time() + 3600
        self.day_reset_time = time.time() + 86400
        
        logger.info(f"Rate limiter initialized with limits: {self.config}")
    
    def record_request(self) -> None:
        """
        Record a successful API request.
        
        This method should be called after each successful API request to
        properly track usage against rate limits.
        """
        with self.lock:
            current_time = time.time()
            self.request_history.append(current_time)
            
            # Check if we need to reset any counters
            if current_time > self.minute_reset_time:
                self.minute_reset_time = current_time + 60
                
            if current_time > self.hour_reset_time:
                self.hour_reset_time = current_time + 3600
                
            if current_time > self.day_reset_time:
                self.day_reset_time = current_time + 86400
    
    def can_proceed(self) -> bool:
        """
        Check if a new request can proceed based on current rate limits.
        
        Returns:
            True if the request can proceed, False otherwise
        """
        with self.lock:
            current_time = time.time()
            
            # Count requests in the last minute, hour, and day
            minute_ago = current_time - 60
            hour_ago = current_time - 3600
            day_ago = current_time - 86400
            
            minute_requests = sum(1 for t in self.request_history if t > minute_ago)
            hour_requests = sum(1 for t in self.request_history if t > hour_ago)
            day_requests = sum(1 for t in self.request_history if t > day_ago)
            
            # Check if any rate limits are exceeded
            if minute_requests >= self.requests_per_minute:
                logger.warning("Rate limit exceeded: requests per minute")
                return False
                
            if hour_requests >= self.requests_per_hour:
                logger.warning("Rate limit exceeded: requests per hour")
                return False
                
            if day_requests >= self.requests_per_day:
                logger.warning("Rate limit exceeded: requests per day")
                return False
                
            if self.active_requests >= self.concurrent_requests:
                logger.warning("Rate limit exceeded: concurrent requests")
                return False
                
            # Increment active requests count since we're allowing this request
            self.active_requests += 1
            return True
    
    def release_request(self) -> None:
        """
        Mark an active request as completed.
        
        This method should be called after a request is completed to decrement
        the active requests counter.
        """
        with self.lock:
            if self.active_requests > 0:
                self.active_requests -= 1
    
    def get_remaining_requests(self) -> Dict[str, int]:
        """
        Get the number of remaining requests allowed for each time window.
        
        Returns:
            Dictionary with remaining requests for each time window
        """
        with self.lock:
            current_time = time.time()
            
            # Count requests in the last minute, hour, and day
            minute_ago = current_time - 60
            hour_ago = current_time - 3600
            day_ago = current_time - 86400
            
            minute_requests = sum(1 for t in self.request_history if t > minute_ago)
            hour_requests = sum(1 for t in self.request_history if t > hour_ago)
            day_requests = sum(1 for t in self.request_history if t > day_ago)
            
            return {
                'per_minute': max(0, self.requests_per_minute - minute_requests),
                'per_hour': max(0, self.requests_per_hour - hour_requests),
                'per_day': max(0, self.requests_per_day - day_requests),
                'concurrent': max(0, self.concurrent_requests - self.active_requests)
            }
    
    def get_retry_after(self) -> int:
        """
        Get the recommended wait time in seconds before retrying a request
        when a rate limit is exceeded.
        
        Returns:
            Seconds to wait before retrying
        """
        with self.lock:
            current_time = time.time()
            
            # If we're at the minute limit, wait until the next minute reset
            if self.get_remaining_requests()['per_minute'] == 0:
                return max(1, int(self.minute_reset_time - current_time))
                
            # If we're at the hour limit, wait until the next hour reset
            if self.get_remaining_requests()['per_hour'] == 0:
                return max(1, int(self.hour_reset_time - current_time))
                
            # If we're at the day limit, wait until the next day reset
            if self.get_remaining_requests()['per_day'] == 0:
                return max(1, int(self.day_reset_time - current_time))
                
            # If we're at the concurrent limit, wait a short time
            if self.get_remaining_requests()['concurrent'] == 0:
                return 1
                
            # Default wait time
            return 1
    
    def get_reset_time(self) -> Dict[str, float]:
        """
        Get the time when each rate limit will reset.
        
        Returns:
            Dictionary with reset times for each time window
        """
        return {
            'minute': self.minute_reset_time,
            'hour': self.hour_reset_time,
            'day': self.day_reset_time
        }
    
    def update_limits(self, config: Dict[str, Any]) -> None:
        """
        Update rate limit configuration.
        
        Args:
            config: New rate limit configuration
        """
        with self.lock:
            self.config.update(config)
            
            # Update rate limits
            self.requests_per_minute = self.config.get('requests_per_minute', self.requests_per_minute)
            self.requests_per_hour = self.config.get('requests_per_hour', self.requests_per_hour)
            self.requests_per_day = self.config.get('requests_per_day', self.requests_per_day)
            self.concurrent_requests = self.config.get('concurrent_requests', self.concurrent_requests)
            
            # Update request history max length
            self.request_history = deque(self.request_history, maxlen=max(self.requests_per_day, 10000))
            
            logger.info(f"Rate limiter updated with new limits: {self.config}")
    
    def reset_counters(self) -> None:
        """
        Reset all rate limit counters.
        
        This method can be used to clear rate limit history, for example
        when API credentials change or when testing.
        """
        with self.lock:
            current_time = time.time()
            self.request_history.clear()
            self.active_requests = 0
            self.minute_reset_time = current_time + 60
            self.hour_reset_time = current_time + 3600
            self.day_reset_time = current_time + 86400
            
            logger.info("Rate limiter counters reset")