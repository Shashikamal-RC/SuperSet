import time
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def send_slack_notification(message: str, slack_token: str, channel: str = '#general'):
    client = WebClient(token=slack_token)

    try:
        response = client.chat_postMessage(
            channel=channel,
            text=message
        )
        return response
    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")
        return None
