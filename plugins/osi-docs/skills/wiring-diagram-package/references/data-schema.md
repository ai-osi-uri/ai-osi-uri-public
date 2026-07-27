# Network Source Schema

`network-source.json` は画像認識、確認、構成図、BOMの単一正本である。IDは版をまたいで安定させる。

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "Example Site",
    "revision": 1,
    "source_files": ["drawing-01.jpg"],
    "confirmed_at": null
  },
  "locations": [
    {
      "id": "loc-001",
      "name": "1F office",
      "parent_id": null
    }
  ],
  "devices": [
    {
      "id": "dev-001",
      "location_id": "loc-001",
      "role": "switch",
      "label": "SW-01",
      "vendor": null,
      "model": null,
      "quantity": 1,
      "status": "existing",
      "confidence": 0.92,
      "source_refs": ["drawing-01.jpg#xywh=120,80,260,140"]
    }
  ],
  "ports": [
    {
      "id": "port-001",
      "device_id": "dev-001",
      "label": "Gi1/0/1",
      "media": "copper"
    }
  ],
  "connections": [
    {
      "id": "conn-001",
      "from_port_id": "port-001",
      "to_port_id": "port-002",
      "media": "cat6",
      "length_m": null,
      "label": "C-001",
      "confidence": 0.81,
      "source_refs": ["drawing-01.jpg#xywh=210,120,480,260"]
    }
  ],
  "networks": [
    {
      "id": "net-001",
      "name": "Office LAN",
      "cidr": null,
      "vlan_id": null
    }
  ],
  "uncertainties": [
    {
      "id": "unc-001",
      "priority": "P0",
      "field": "connections.conn-001.to_port_id",
      "question": "接続先はAP-01で正しいですか",
      "status": "open",
      "resolution": null
    }
  ]
}
```

## Required Rules

- `devices.id`、`ports.id`、`connections.id` は一意。
- 全ポートは存在する機器を参照する。
- 全接続は両端ポートを参照する。未確定時は `uncertainties` に理由を持つ。
- `confidence` は0〜1。ユーザー確認済み項目は `1.0` にして確認履歴を残す。
- `status` は `existing`、`new`、`remove`、`tbd` のいずれか。
- BOMへ入る数量は `quantity` と接続集計から導出し、手入力で二重管理しない。
