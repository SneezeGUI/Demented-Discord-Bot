import aiohttp
import asyncio
import logging

logger = logging.getLogger('demented_bot.session')

# Simple global session manager
class SessionManager:
    session = None
    
    @classmethod
    def get_session(cls):
        """Get a shared aiohttp ClientSession, creating it if needed."""
        if cls.session is None or cls.session.closed:
            cls.session = aiohttp.ClientSession()
            logger.info("Created new shared HTTP session")
        return cls.session
    
    @classmethod
    async def close(cls):
        """Close the shared session if it exists."""
        if cls.session and not cls.session.closed:
            await cls.session.close()
            cls.session = None
            logger.info("Closed shared HTTP session")

# Imports for caching
import time
from datetime import datetime, timedelta
from functools import lru_cache

# Simple time-based caching for API requests
class SimpleCache:
    cache = {}
    _last_cleanup = time.monotonic()  # Use monotonic time for expirations
    _cleanup_interval = 300  # Cleanup every 5 minutes
    
    @classmethod
    def get(cls, key):
        """Get an item from cache if it exists and is not expired.
        Will periodically clean expired items to prevent memory leaks.
        """
        # Occasionally clean expired entries
        now = time.monotonic()
        if now - cls._last_cleanup > cls._cleanup_interval:
            cls._clear_expired_entries()
            cls._last_cleanup = now
            
        # Check if key exists and is not expired
        if key in cls.cache:
            data, expiry = cls.cache[key]
            if now < expiry:
                return data
            # Remove expired item
            del cls.cache[key]
        return None
    
    @classmethod
    def set(cls, key, data, ttl_seconds=3600):
        """Store an item in cache with expiration time."""
        expiry = time.monotonic() + ttl_seconds  # More efficient than datetime
        cls.cache[key] = (data, expiry)
    
    @classmethod
    def _clear_expired_entries(cls):
        """Remove all expired items from cache."""
        now = time.monotonic()
        expired_keys = [k for k, (_, exp) in cls.cache.items() if now >= exp]
        for key in expired_keys:
            del cls.cache[key]
        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired cache items")
    
    @classmethod
    def clear_all(cls):
        """Clear all cached entries."""
        size = len(cls.cache)
        cls.cache.clear()
        logger.debug(f"Cleared all {size} cache entries")

# Enhanced HTTP fetch with caching
async def cached_http_get(url, params=None, ttl_seconds=3600, method="get", json_data=None, headers=None, timeout=10):
    """Make an HTTP request with caching support.
    
    Args:
        url: The URL to request
        params: Optional query parameters
        ttl_seconds: How long to cache results (0 to disable)
        method: HTTP method to use ('get', 'post', etc)
        json_data: JSON data for POST requests
        headers: Request headers
        timeout: Request timeout in seconds
        
    Returns:
        Response data, or None if request failed
    """
    # Skip cache for non-GET requests
    use_cache = ttl_seconds > 0 and method.lower() == 'get'
    
    # Generate cache key (only for cacheable requests)
    if use_cache:
        # Create a more compact key
        param_str = '-'.join(f"{k}:{v}" for k, v in sorted(params.items())) if params else ""
        cache_key = f"{url}:{param_str}"
        
        # Try cache first
        cached_data = SimpleCache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit for {url}")
            return cached_data
    
    # Get shared session
    session = SessionManager.get_session()
    
    try:
        # Make the request
        request_method = getattr(session, method.lower())
        
        # Build request kwargs
        kwargs = {
            'timeout': aiohttp.ClientTimeout(total=timeout)
        }
        if params:
            kwargs['params'] = params
        if json_data:
            kwargs['json'] = json_data
        if headers:
            kwargs['headers'] = headers
        
        # Execute request
        async with request_method(url, **kwargs) as response:
            # Handle non-200 status
            if response.status != 200:
                logger.warning(f"API returned status {response.status} for {url}")
                return None
                
            # Try to parse JSON, fall back to text
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                data = await response.text()
            
            # Cache the result if appropriate
            if use_cache:
                SimpleCache.set(cache_key, data, ttl_seconds)
                
            return data
                
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"HTTP error for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None