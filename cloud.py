import os
from google.cloud import pubsub_v1


def pub(message):
    client = pubsub_v1.PublisherClient()
    topic_path = client.topic_path(
        project=os.getenv('GOOGLE_CLOUD_PROJECT'),
        topic=os.getenv('GOOGLE_PUBSUB_TOPIC'),
    )
    future = client.publish(topic_path, str(message).encode(), attr='ATTR VALUE')
    future.result()
