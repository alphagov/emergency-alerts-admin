from emergency_alerts_utils.clients.antivirus.antivirus_client import AntivirusClient
from emergency_alerts_utils.clients.redis.redis_client import RedisClient
from emergency_alerts_utils.clients.zendesk.zendesk_client import ZendeskClient

antivirus_client = AntivirusClient()
zendesk_client = ZendeskClient()
redis_client = RedisClient()
