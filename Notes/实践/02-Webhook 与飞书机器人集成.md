审计告警功能需要把检测到的安全事件推送到飞书群。飞书提供了自定义机器人 Webhook 的接口，支持文本和富文本消息格式，也可以配置 HMAC-SHA256 签名验证。

实现上需要解决三个问题：签名怎么算、参数放哪里、消息怎么写。

## 签名算法

飞书官方文档给出的签名示例：

```python
import hashlib
import base64
import hmac

def gen_sign(timestamp, secret):
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign
```

注意这里的 `hmac.new` 调用是 `hmac.new(key, msg=None, digestmod=sha256)`，key 是 `timestamp\nsecret`，msg 为空。和通常的 `hmac.new(secret, data, digestmod)` 写法不一样，如果习惯性地把 secret 放第一个参数、string_to_sign 放第二个，签名就对不上。

## 时间戳单位

飞书用的是秒（`int(time.time())`）。如果写成了 `time.time() * 1000`，服务端验签就会失败。

```python
# 飞书：用秒
timestamp = str(int(time.time()))

timestamp = str(int(time.time() * 1000))
```

## 参数位置

另一个容易踩坑的地方是 `timestamp` 和 `sign` 参数放在哪里。最初的习惯是把它们作为 URL 查询参数拼在 Webhook 地址后面：

```
https://open.feishu.cn/open-apis/bot/v2/hook/xxx?timestamp=xxx&sign=xxx
```

飞书实际要求的是放在 JSON body 里：

```json
{
    "timestamp": "1742821707",
    "sign": "xxxxxx",
    "msg_type": "text",
    "content": {"text": "消息内容"}
}
```

拼在 URL 上也不会报错，但签名校验通不过。

## 消息格式

飞书自定义机器人支持多种消息类型。最常用的是文本格式：

```json
{
    "msg_type": "text",
    "content": {
        "text": "消息正文"
    }
}
```

富文本（post）格式支持更复杂的排版：

```json
{
    "msg_type": "post",
    "content": {
        "post": {
            "zh_cn": {
                "title": "标题",
                "content": [
                    [{
                        "tag": "text",
                        "text": "说明文字"
                    }, {
                        "tag": "a",
                        "text": "链接文字",
                        "href": "http://example.com"
                    }]
                ]
            }
        }
    }
}
```

## 测试验证

Webhook 配置页面上加了一个测试按钮，填好 Webhook URL 和可选签名密钥后可以直接发一条测试消息到群聊。后端对应一个测试端点，复用同样的签名和发送逻辑。

不填密钥时直接发送，收不到说明 URL 或网络有问题。填了密钥收不到，说明签名计算和服务端预期的不一致，排查上面三个点。

![](assets/Pasted%20image%2020260724193448.png)


![](assets/Pasted%20image%2020260724193530.png)
