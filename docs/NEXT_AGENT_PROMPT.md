# SmartNews - Next Agent Prompt (Updated 2026-03-09)

> Ilk is olarak `AGENT_HANDOFF.md` dosyasini oku. Bu dosya tek dogru kaynak.

## Mevcut Durum

- Layers 0-5: complete and deployed
- Layer 6B v2: shipped (topic trend page + cluster trend panel + history API)
- Layer 6C: complete
- Layer 7A: complete
- Databricks Job ID: `690227811640184`

## Kritik Acik Konu

1. Azure OpenAI embedding deployment eksik olabilir:
   - `text-embedding-3-small` deploymentini Azure Portal'da olustur.

## Yurutme Sirasi (High Mode)

1. P0 (Days 1-2): 6B v2 production closure
   - API/frontend deploy green oldugunu dogrula.
   - `/api/topics/{topic}/history`, `/topic/[name]`, `/clusters/[id]` smoke test.
   - Ikinci gun pipeline run alip trend verisini cizgi grafige tasiyacak kadar biriktir.

2. P1 (Day 3): Embedding blocker removal
   - `text-embedding-3-small` deploymentini olustur.
   - Pipeline calistir, embedding backfill dogrula.

3. P2 (Days 4-5): 5C quick win
   - Homepage/search card'larina `Original / De-hyped` toggle ekle.

4. P3 (Days 6-8): 6D MVP
   - credibility sub-signals ekle (source_reputation, specificity, attribution_quality, evidence_strength).
   - API + frontend detail visualizasyonu tamamla.

5. P4 (Days 9-10): 7B scope freeze
   - Narrative Tracker icin karar-tam teknik spec ve backlog cikart.

## Kurallar

- `python` yerine her zaman: `C:\Users\haktan\.local\bin\uv.exe run python`
- Notebook degisikliginde: `deploy_to_databricks.py` ile workspace upload et.
- Gold tablolari frontend tarafindan direkt sorgulanmaz.
- Job ID degisirse `AGENT_HANDOFF.md` ve ilgili dokumanlari guncelle.
