# NEO Explorer — مستكشف الأجرام القريبة من الأرض

أداة سطر أوامر (CLI) تقرأ بيانات NASA/JPL الحقيقية عن **الأجرام القريبة من الأرض** (Near-Earth Objects) واقتراباتها من الأرض، تربطها في الذاكرة، وتتيح البحث والاستكشاف والتصدير.

يقرأ النظام ملفين:
- **`neos.csv`** — كتالوج الأجرام (تعريف، اسم، قطر، هل يمثّل خطرًا).
- **`cad.json`** — سجل الاقترابات القريبة (زمن، مسافة، سرعة، والـ`designation` الرابط).

---

## المزايا

- تحميل وتحليل CSV + JSON إلى كائنات Python.
- ربط ثنائي الاتجاه بين كل جرم واقتراباته.
- بحث بمعايير **قابلة للتركيب** عبر **Strategy Pattern**.
- واجهة موحّدة رقيقة للـCLI عبر **Facade Pattern**.
- تصدير النتائج إلى CSV أو JSON.
- **صفر تبعيات تشغيل** (مكتبة Python القياسية فقط).

---

## المتطلبات والتشغيل

- Python ≥ 3.10 (بلا تبعيات خارجية).

```bash
# يعمل مباشرة على العيّنات الافتراضية بلا وسائط
python -m neo_explorer query

# مع بياناتك الحقيقية
python -m neo_explorer --neos data/neos.csv --cad data/cad.json query --hazardous

# أو بعد التثبيت (يوفّر الأمر neo-explorer)
pip install -e .
neo-explorer inspect --name Halley
```

> المسارات الافتراضية هي العيّنات `data/neos.sample.csv` و`data/cad.sample.json`، فيعمل النظام out-of-box. مرّر `--neos`/`--cad` لبياناتك الحقيقية.

---

## أوامر الاستخدام

### `query` — البحث في الاقترابات

```bash
python -m neo_explorer --neos data/neos.sample.csv --cad data/cad.sample.json \
    query --hazardous --max-distance 0.03 --limit 10
```

| الخيار | المعنى |
|--------|--------|
| `--date YYYY-MM-DD` | اقترابات في تاريخ محدد |
| `--start-date` / `--end-date` | نطاق زمني |
| `--min-distance` / `--max-distance` | حدود المسافة (au) |
| `--min-velocity` / `--max-velocity` | حدود السرعة (km/s) |
| `--min-diameter` / `--max-diameter` | حدود القطر (km) |
| `--hazardous` / `--no-hazardous` | قصر على (أو استبعاد) الخطِرة |
| `--limit N` | حدّ النتائج (0 = بلا حدّ) |
| `--outfile out.csv` / `out.json` | تصدير بدل الطباعة |

| `--min-*` أكبر من `--max-*` | يُرفَض برسالة خطأ واضحة (وكذلك `--start-date` بعد `--end-date`) |
| `--limit` سالب | يُرفَض برسالة خطأ |

### `inspect` — فحص جرم واحد

```bash
python -m neo_explorer inspect --name Alpha
python -m neo_explorer inspect --designation "2020 AB" --verbose   # يعرض اقترابات الجرم أيضًا
```

| الخيار | المعنى |
|--------|--------|
| `--designation` / `--name` | تحديد الجرم (أحدهما مطلوب) |
| `--verbose` | عرض قائمة اقترابات الجرم بعد وصفه |

---

## بنية المشروع

```
neo_explorer/
├── data/                 عيّنات البيانات (CSV/JSON)
└── neo_explorer/
    ├── models.py         NearEarthObject / CloseApproach   (كائنات المجال + __str__)
    ├── extract.py        load_neos / load_approaches        (قراءة الملفات وبناء الكائنات)
    ├── database.py       NEODatabase                        (فهرسة + ربط + بثّ الاستعلام)
    ├── filters.py        FilterStrategy + الاستراتيجيات      (Strategy Pattern)
    ├── facade.py         NEOExplorerFacade                  (Facade Pattern)
    ├── write.py          write_to_csv / write_to_json       (تصدير)
    ├── display.py        print_approaches / print_neo       (طباعة الطرفية)
    ├── cli.py            محوّل الأوامر                        (argparse → facade)
    └── __main__.py       نقطة الدخول
```

| الوحدة | المسؤولية | النوع |
|--------|-----------|------|
| `models.py` | كائنات بيانات المجال و`__str__` فقط — لا I/O، لا parsing | Classes |
| `extract.py` | قراءة CSV/JSON، تحويل الأنواع، تجاهل الحقول الزائدة | Standalone functions |
| `database.py` | حفظ المجموعات، بناء الفهارس، الربط، `query()` كسول | Class |
| `filters.py` | عقد `FilterStrategy` + استراتيجيات + `create_filters` | Strategy |
| `facade.py` | واجهة موحّدة رقيقة تنسّق بقية الطبقات | Facade |
| `write.py` / `display.py` | التصدير / الطباعة | Standalone functions |
| `cli.py` | قراءة الوسائط → فلاتر → facade → عرض/تصدير | Adapter رقيق |

---

## المعمارية

### الطبقات (اتجاه أحادي، بلا دورات)

```
        ┌──────────────────────────────────────────────┐
        │  cli.py  (adapter: args → filters → facade)   │  ← الدخول/العرض
        └───────────────┬───────────────────────────────┘
                        │ يعرف Facade فقط
        ┌───────────────▼───────────────────────────────┐
        │  facade.py — NEOExplorerFacade  (تنسيق رقيق)   │  ← الواجهة الموحّدة
        └───┬──────────────┬───────────────┬─────────────┘
            │              │               │
   ┌────────▼──────┐ ┌─────▼───────┐ ┌─────▼──────────┐
   │  extract.py   │ │ database.py │ │   filters.py    │  ← منطق الأعمال
   └───────┬───────┘ └─────┬───────┘ └─────┬──────────┘
           └───────────────▼───────────────┘
                    ┌──────────────┐
                    │  models.py   │  ← المجال (لا يعتمد على أحد)
                    └──────────────┘

   write.py / display.py  ← الإخراج (يستدعيها الـCLI، تعتمد على models فقط)
```

القاعدة: الاعتماد يتجه للأسفل فقط. `models` نقيّ لا يعرف أي طبقة، والـCLI لا يعرف إلا الـFacade.

### الأنماط المستخدَمة

**① Strategy Pattern** — `filters.py`
كل معيار تصفية استراتيجية `@dataclass(frozen=True)` تحقّق العقد `matches(approach) -> bool`. تُركَّب المعايير عبر `all(f.matches(a) for f in filters)` داخل `query`، فإضافة معيار جديد = **صنف جديد فقط** دون تعديل الاستعلام (OCP).

**② Facade Pattern** — `facade.py`
`NEOExplorerFacade` يوفّر واجهة صغيرة (`from_files`, `get_neo_by_designation`, `get_neo_by_name`, `search`) ويفوّض العمل إلى الطبقات الداخلية — بلا parsing/linking/formatting بداخله. الواجهة الصغيرة وحدود المسؤولية تقلّلان خطر تحوّله إلى God Object.

> لا أنماط أخرى عمدًا (لا Repository/Factory/ORM) — التزامًا بـKISS/YAGNI.

### مبادئ التصميم

| المبدأ | التطبيق |
|--------|---------|
| SRP | كل وحدة مسؤولية واحدة |
| OCP | معيار تصفية جديد لا يلمس الاستعلام |
| DIP | الـCLI يعتمد على تجريد Facade؛ الـFacade تُحقَن بـ`NEODatabase` |
| SoC | Domain / Extract / Storage / Filter / Presentation / Export منفصلة |
| DRY | تحويل مركزي في extract؛ `_diameter_or_nan` وnormalization في مكان واحد |
| KISS / YAGNI | قواميس بدل قاعدة بيانات؛ دوال حرة حيث لا حالة؛ لا abstractions زائدة |
| Composition over inheritance | تركيب الفلاتر والـDB بدل هرميات وراثة |

---

## تدفق البيانات (من البداية للنهاية)

مثال: `query --hazardous --max-distance 0.03`

```
1. cli.main() → argparse ينتج الوسائط
2. NEOExplorerFacade.from_files(neos, cad)          ← التحميل مرة واحدة
     ├─ extract.load_neos(csv)       → tuple[NearEarthObject]   (concrete)
     ├─ extract.load_approaches(json)→ tuple[CloseApproach]      (concrete، designation مؤقت، neo=None)
     └─ NEODatabase(neos, approaches):
           ├─ يبني فهرس designation (strip، تكرار→ValueError)
           ├─ يبني فهرس name (strip+casefold، أول-يفوز)
           └─ link(): لكل approach → approach.neo = neo ، وneo.approaches.append(approach)
                        (بلا مطابقة → neo يبقى None: اقتراب يتيم باقٍ)
3. create_filters(...) → [MaxDistanceFilter(0.03), HazardousFilter(True)]
4. facade.search(filters, limit=10):
     └─ database.query(filters)  ← generator: yield approach if all(f.matches(approach))
     └─ islice(results, 10)      ← الحدّ بلا تحويل لقائمة
5. display.print_approaches(results) ← يستهلك الـgenerator ويطبع
```

### قرارات البيانات

- **القطر المفقود** = `float("nan")` (لا `None`)، يُفحَص بـ`math.isnan`؛ فلاتر القطر لا تطابق المجهول.
- **الاقتراب اليتيم** (بلا جرم مطابق): `neo=None`، يبقى في القاعدة، لا ينهار البحث/العرض بسببه.
- **الوقت** بتوقيت UTC (`datetime`).
- **concrete مقابل streaming**: البيانات المحمّلة والفهارس **concrete** (tuple/dict)؛ نتائج الاستعلام والحدّ **streaming** (generator + `islice`).
- **الحقول الزائدة** في CSV/JSON تُتجاهَل ولا تُربَط بالكائنات.
- **البيانات المعطوبة** (عمود `pdes` ناقص، حقل مفقود، قيمة غير رقمية) تُنتج رسالة خطأ واضحة مع رقم السطر/الصف بدل انهيار خام.

---

## الاختبار

```bash
pip install -e ".[dev]"
pytest        # اختبارات لكل طبقة: models / extract / database / filters / facade
ruff check .  # فحص الأسلوب (PEP 8)
```

تغطّي الاختبارات: توزيع الخصائص، سياسة NaN، الربط الثنائي، الاقتراب اليتيم، normalization، تكرار المفاتيح، تركيب الفلاتر، والبثّ الكسول.
