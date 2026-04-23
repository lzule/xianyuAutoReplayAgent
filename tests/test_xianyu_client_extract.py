from app.channel.xianyu_client import XianyuChannelClient


def build_client() -> XianyuChannelClient:
    cookies = "_m_h5_tk=abc_123; unb=3530268654; cookie2=x; sgcookie=y; cna=z"
    return XianyuChannelClient(
        cookies_str=cookies,
        websocket_url="wss://wss-goofish.dingtalk.com/",
        heartbeat_interval=15,
        heartbeat_timeout=5,
        message_expire_ms=300000,
    )


def test_extract_chat_message_with_int_keys() -> None:
    client = build_client()
    message = {
        1: {
            2: "47812870000@goofish",
            5: 32503680000000,
            10: {
                "reminderContent": "你好，怎么收费？",
                "senderUserId": "123456",
                "reminderTitle": "客户A",
                "reminderUrl": "https://www.goofish.com/?itemId=900052644277",
            },
        }
    }
    chat = client._extract_chat_message(message)
    assert chat is not None
    assert chat.chat_id == "47812870000"
    assert chat.sender_id == "123456"
    assert chat.item_id == "900052644277"


def test_extract_chat_message_with_str_keys() -> None:
    client = build_client()
    message = {
        "1": {
            "2": "47812870000@goofish",
            "5": 32503680000000,
            "10": {
                "reminderContent": "你好",
                "senderUserId": "123456",
                "reminderTitle": "客户B",
            },
        }
    }
    chat = client._extract_chat_message(message)
    assert chat is not None
    assert chat.sender_name == "客户B"
