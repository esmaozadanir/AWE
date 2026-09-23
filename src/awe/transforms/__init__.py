"""Servise özel TRANSFORM kodunun yaşadığı yer -- `awe.pull.fetch_raw_data`nın döndürdüğü ham
veriyi, o projenin `AdapterMapping`'inin beklediği canonical event şekline çevirir.

Bu adım kasıtlı olarak jenerik DEĞİLDİR (bkz. `awe.services.sync` modül docstring'i, `docs/
engine-decisions.md`): her dış servis "bir kullanıcı şu işlemi yaptı" bilgisini kendi, keyfi
JSON şeklinde taşır -- config değerleriyle ifade edilemez, gerçek kod ister.

Yeni bir servis eklerken: `awe/transforms/{project_id}.py` adında bir modül oluştur, içine
`def transform(raw_data: object) -> list[dict]:` fonksiyonu yaz (bkz. `config_examples/*.yaml`
dosyalarındaki `mapping:` bölümünün beklediği ham event alan adları). `awe.services.sync`,
`project_id`e göre bu modülü otomatik bulur (dosya adı kuralı -- `ProjectRegistry`nin
`config_examples/{project_id}.yaml`i bulma şekliyle aynı desen)."""
