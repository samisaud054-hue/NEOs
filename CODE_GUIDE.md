# دليل الكود (Code Guide) — شرح كل ملف تنفيذي

هذا الملف مرجع للمهندس لفهم كل وحدة في المشروع: **ماذا تفعل، مكوّناتها، كيف تعمل، ولماذا صُمّمت هكذا، وكيف تتصل بغيرها**.

ترتيب الشرح يتبع تدفّق البيانات: من المجال → التحميل → التخزين → التصفية → الواجهة → الإخراج → الدخول.

```
models → extract → database → filters → facade → (display / write) → cli → __main__
```

جدول سريع:

| الملف | الطبقة | يصدّر | يعتمد على |
|-------|--------|-------|-----------|
| `models.py` | المجال | `NearEarthObject`, `CloseApproach` | — (stdlib فقط) |
| `extract.py` | تحميل | `load_neos`, `load_approaches` | `models` |
| `database.py` | تخزين+ربط | `NEODatabase` | `models`, `filters` |
| `filters.py` | تصفية | `FilterStrategy`, الاستراتيجيات, `create_filters` | `models` |
| `facade.py` | واجهة | `NEOExplorerFacade` | `extract`, `database`, `filters`, `models` |
| `display.py` | إخراج | `print_approaches`, `print_neo` | `models` |
| `write.py` | إخراج | `write_to_csv`, `write_to_json` | `models` |
| `cli.py` | دخول | `main` | `facade`, `filters`, `display`, `write`, `models` |
| `__main__.py` | دخول | — | `cli` |
| `__init__.py` | حزمة | صادرات عامة | `models`, `database`, `facade` |

---

## 1) `models.py` — كائنات المجال

**ماذا يفعل:** يعرّف الكيانين الأساسيين للنظام كحاملي بيانات نقيّين. لا يقرأ ملفات، لا يطبع، لا يحوّل نصوصًا خام. كل كيان يوفّر `__str__` لوصف مقروء.

### `class NearEarthObject`
جرم قريب من الأرض.

| الخاصية | النوع | المعنى |
|---------|------|--------|
| `designation` | `str` | المُعرِّف الأساسي (فريد) |
| `name` | `str \| None` | الاسم الرسمي (قد يكون `None`) |
| `diameter` | `float` | القطر بالكيلومتر، أو `float("nan")` إن كان مجهولًا |
| `hazardous` | `bool` | هل يمثّل خطرًا |
| `approaches` | `list[CloseApproach]` | اقترابات هذا الجرم (تبدأ فارغة، تملؤها `NEODatabase`) |

- `fullname` (property): يجمع الـdesignation والاسم بشكل مقروء.
- `__str__`: يستخدم `math.isnan(self.diameter)` للتعبير عن القطر المجهول.

### `class CloseApproach`
اقتراب واحد من الأرض في لحظة زمنية.

| الخاصية | النوع | المعنى |
|---------|------|--------|
| `designation` | `str` | designation الجرم المقترب — **يبقى بعد الربط** ويُستخدَم للربط |
| `time` | `datetime` | لحظة الاقتراب (UTC) |
| `distance` | `float` | المسافة (وحدة فلكية au) |
| `velocity` | `float` | السرعة النسبية (km/s) |
| `neo` | `NearEarthObject \| None` | مرجع الجرم — يبدأ `None`، تسنده `NEODatabase` |

- `date` (property): تاريخ الاقتراب (بلا وقت) — يستخدمه فلتر التاريخ.
- `__str__`: يعمل حتى لو `neo=None` (اقتراب يتيم) عبر الرجوع إلى `designation`.

**لماذا هكذا:** فصل المجال يمنع تسرّب الـparsing/الطباعة إليه (SoC). النماذج **قابلة للتعديل** (غير frozen) لأن الربط يسند `neo` ويملأ `approaches`.

---

## 2) `extract.py` — قراءة الملفات وبناء الكائنات

**ماذا يفعل:** دالتان مستقلتان (standalone) تقرآن ملفَي البيانات، تحوّلان القيم الخام إلى أنواعها، وتنشئان كائنات المجال. تتجاهلان الأعمدة/الحقول الزائدة. البيانات المعطوبة تُنتج `ValueError` واضحًا برقم السطر/الصف.

### `load_neos(path) -> tuple[NearEarthObject, ...]`
- يفتح CSV بـ`csv.DictReader`.
- يتحقّق من وجود عمود `pdes` (وإلا `ValueError` صريح).
- لكل صف ينشئ `NearEarthObject`: `pdes`→designation, `name`, `diameter`(→NaN إن فارغ), `pha`(→bool).
- يلتقط أخطاء التحويل ويعيد رميها مع رقم السطر.
- **يعيد `tuple`** (بيانات concrete معروفة الحجم).

### `load_approaches(path) -> tuple[CloseApproach, ...]`
- يفتح JSON بـ`json.load` → dict فيه `fields` و`data`.
- يبني خريطة `field → index` ويتحقّق من الحقول المطلوبة `des, cd, dist, v_rel`.
- لكل صف يقرأ **هذه الحقول فقط** (تجاهل الزائد) وينشئ `CloseApproach` (بـ`neo=None` وdesignation مؤقت).
- **يعيد `tuple`**.

### دوال مساعدة خاصة
| الدالة | الدور |
|--------|------|
| `_clean_name(v)` | نص مقصوص أو `None` إن فارغ |
| `_to_float_or_nan(v)` | `float`، أو `NaN` إن غاب |
| `_to_bool(v)` | `Y/yes/true/1` → `True`، وإلا `False` |
| `_to_datetime(v)` | يجرّب عدة صيغ تاريخ (مثل `2025-Jan-01 12:00`) |

**لماذا standalone functions:** العملية عديمة الحالة ولا تنتمي لكائن (قاعدة Rubric).

---

## 3) `database.py` — الفهرسة والربط والاستعلام

**ماذا يفعل:** `NEODatabase` يخزّن المجموعات المحمّلة، يبني فهارس بحث، **يربط كل اقتراب بجرمه (وبالعكس)**، ويبثّ الاقترابات عبر الفلاتر. لا SQL — قواميس في الذاكرة توفّر بحث O(1).

### `class NEODatabase`

**المُنشئ** `__init__(neos, approaches)`:
1. يحفظ المجموعتين كـ`tuple` (concrete).
2. يبني `_by_designation` (dict).
3. يبني `_by_name` (dict).
4. يستدعي `link()`.

**`link()`** — الربط الثنائي (قابل لإعادة الاستدعاء بأمان):
```
لكل neo:  neo.approaches.clear()          # يمنع التكرار عند إعادة الربط
لكل approach:
    neo = _by_designation.get(normalize(approach.designation))
    approach.neo = neo                      # ربط اتجاه CA → NEO
    if neo: neo.approaches.append(approach) # ربط اتجاه NEO → CA
    # بلا مطابقة → approach.neo يبقى None (يتيم باقٍ)
```

**البحث:**
- `get_neo_by_designation(d)` / `get_neo_by_name(n)`: بحث O(1) بعد التطبيع؛ يعيد `None` للإدخال الفارغ أو غير الموجود.

**الاستعلام:**
- `query(filters=()) -> Iterator[CloseApproach]`: **generator** يمرّ على الاقترابات ويُخرِج ما يطابق `all(f.matches(a) for f in filters)` — **بلا if/elif**، وبلا تحويل لقائمة.

### سياسات الفهرسة (دوال ساكنة خاصة)
| الدالة | السياسة |
|--------|---------|
| `_build_designation_index` | تكرار الـdesignation → `ValueError` (مُعرِّف فريد) |
| `_build_name_index` | يتجاهل الأسماء الفارغة؛ عند التكرار: **أول-يفوز** (`setdefault`) |

### التطبيع (دوال على مستوى الموديول)
| الدالة | العملية |
|--------|---------|
| `_normalize_designation` | `strip()` |
| `_normalize_name` | `strip().casefold()` (بحث غير حسّاس لحالة الأحرف) |

**لماذا هكذا:** الربط والفهرسة سلوك بيانات (ينتمي للـDB لا للنماذج). التطبيع في مكان واحد (DRY). `query` كسول (كفاءة ذاكرة).

---

## 4) `filters.py` — نظام التصفية (Strategy Pattern)

**ماذا يفعل:** يحوّل كل معيار بحث إلى **استراتيجية صغيرة صريحة** تحقّق عقدًا موحّدًا، فتتركّب أي مجموعة معايير بلا منطق تفريعي.

### `class FilterStrategy(Protocol)`
العقد: أي كائن له `matches(approach) -> bool` يُعدّ فلترًا. (Protocol = اقتران بنيوي، بلا وراثة إجبارية.)

### الاستراتيجيات الملموسة (كلها `@dataclass(frozen=True)`)
| الصنف | المعيار |
|-------|---------|
| `DateFilter(on)` | التاريخ يساوي |
| `StartDateFilter(start)` / `EndDateFilter(end)` | نطاق زمني |
| `MinDistanceFilter` / `MaxDistanceFilter` | حدود المسافة |
| `MinVelocityFilter` / `MaxVelocityFilter` | حدود السرعة |
| `MinDiameterFilter` / `MaxDiameterFilter` | حدود القطر (تتعامل مع NaN) |
| `HazardousFilter(hazardous)` | حالة الخطورة (تحرس `neo=None`) |

كل صنف يحمل **معيارًا واحدًا** ويطبّق `matches` واضحًا وآمنًا نوعيًا.

### `create_filters(**criteria) -> list[FilterStrategy]`
- يستقبل معايير المستخدم (كلها اختيارية).
- يبني قائمة الاستراتيجيات المطلوبة فقط (المعيار `None` = لا استراتيجية).
- استدعاء افتراضي بلا معايير → قائمة فارغة تطابق كل شيء.

### `_diameter_or_nan(approach) -> float`
helper واحد يعيد قطر الجرم أو `NaN` (عند `neo=None` أو قطر مجهول) — **يزيل التكرار الوحيد** بين فلترَي القطر.

**لماذا Strategy:** إضافة معيار جديد = صنف جديد فقط، دون لمس `query` (OCP). التركيب يتم بـ`all(...)` (بلا if/elif، بلا تكرار زائد).

---

## 5) `facade.py` — الواجهة الموحّدة (Facade Pattern)

**ماذا يفعل:** `NEOExplorerFacade` هو **نقطة الوصول الوحيدة للـCLI**. ينسّق التحميل والتخزين والتصفية، لكنه **يفوّض** كل عمل فعلي — بلا parsing/linking/formatting بداخله.

### `class NEOExplorerFacade`
| العضو | الدور |
|-------|------|
| `__init__(database)` | يحقن `NEODatabase` (تبعية صريحة، قابلة للـmock) |
| `from_files(neos_path, approaches_path)` (classmethod) | يحمّل عبر `extract` ثم يبني `NEODatabase` ويعيد facade جاهزًا |
| `get_neo_by_designation(d)` | تفويض إلى الـDB |
| `get_neo_by_name(n)` | تفويض إلى الـDB |
| `search(filters=(), limit=None)` | `database.query(filters)` ثم `islice(results, limit)` إن وُجد حدّ — **يبقى streaming** |

**لماذا Facade:** يعزل الـCLI عن الطبقات الداخلية (Low Coupling). الواجهة الصغيرة وحدود المسؤولية تقلّلان خطر تحوّله إلى God Object. `search` يُطبّق الحدّ عبر `islice` دون تحويل لقائمة.

---

## 6) `display.py` — الطباعة للطرفية

**ماذا يفعل:** دوال مستقلة تحوّل كائنات المجال إلى نص وتطبعه. تُبقي منطق العرض خارج الـDB والـFacade.

| الدالة | الدور |
|--------|------|
| `print_approaches(approaches)` | يطبع كل اقتراب؛ إن لم يوجد أي نتيجة يطبع إشعارًا. يستهلك **iterable/generator** (بثّ) |
| `print_neo(neo)` | يطبع الجرم + عدد اقتراباته المعروفة |

**لماذا standalone functions:** العرض عملية عديمة الحالة لا تنتمي لكائن.

---

## 7) `write.py` — التصدير إلى ملفات

**ماذا يفعل:** دوال مستقلة تسلسل الاقترابات إلى CSV أو JSON. لا تصفية، لا طباعة، لا حالة.

| الدالة | الدور |
|--------|------|
| `write_to_csv(approaches, path)` | يكتب CSV بأعمدة ثابتة؛ القطر المجهول → `""` |
| `write_to_json(approaches, path)` | يكتب قائمة كائنات JSON؛ القطر المجهول → `null` |
| `_serialize(approach, *, nan_diameter)` (خاص) | يبني سجلًّا مسطّحًا؛ يعالج `neo=None` (اليتيم) والاسم الفارغ والقطر NaN |

الأعمدة: `datetime_utc, distance_au, velocity_km_s, designation, name, diameter_km, potentially_hazardous`.

**لماذا هكذا:** التسلسل خارج النماذج (Rubric يمنع serialization في المجال). صيغة NaN تختلف بين CSV (`""`) وJSON (`null`) لإنتاج مخرجات صالحة.

---

## 8) `cli.py` — محوّل سطر الأوامر

**ماذا يفعل:** محوّل رقيق: يقرأ الوسائط، يحوّلها إلى فلاتر، يطلب من الـFacade، ويوجّه النتائج للعرض/التصدير. **بلا parsing/linking/filtering بداخله.**

### الدوال العامة والخاصة
| الدالة | الدور |
|--------|------|
| `main(argv=None)` | يبني الـparser، يحمّل الـFacade، ينفّذ المعالِج المناسب. يلتقط `FileNotFoundError/ValueError/KeyError/TypeError` ويحوّلها لرسالة خطأ أنيقة |
| `_build_parser()` | يبني argparse: `--neos`/`--cad` (افتراضها العيّنات) + أمرا `query` و`inspect` |
| `_add_query_command` | يسجّل خيارات `query` (التاريخ/المسافة/السرعة/القطر/hazardous/limit/outfile) |
| `_add_inspect_command` | يسجّل `inspect` (`--designation`/`--name` حصريًا + `--verbose`) |
| `_run_query(facade, args)` | يتحقّق من النطاقات → `create_filters` → `facade.search` → طباعة أو تصدير |
| `_run_inspect(facade, args)` | يجلب الجرم؛ إن وُجد يطبعه (و`--verbose` يعرض اقتراباته)؛ وإلا يعيد 1 |
| `_export(results, outfile)` | يختار `write_to_csv`/`write_to_json` حسب اللاحقة |
| `_validate_ranges(args)` | يرفض `min > max` (مسافة/سرعة/قطر) و`start_date > end_date` |
| `_non_negative_float` / `_non_negative_int` | أنواع argparse ترفض القيم السالبة |

**تدفّق أمر واحد:** `argv → parse_args → from_files → create_filters → facade.search → display/write`.

**لماذا هكذا:** الـCLI طبقة عرض/دخول فقط؛ كل منطق الأعمال في الطبقات الأدنى (SoC + Low Coupling).

---

## 9) `__main__.py` — نقطة الدخول

**ماذا يفعل:** يمكّن `python -m neo_explorer`. سطر واحد فعّال:
```python
from .cli import main
raise SystemExit(main())
```
يستدعي `main()` ويحوّل قيمة الإرجاع إلى رمز خروج للنظام.

---

## 10) `__init__.py` — واجهة الحزمة

**ماذا يفعل:** يحدّد ما تصدّره الحزمة للاستيراد المباشر، ويحمل docstring الحزمة.

يصدّر عبر `__all__`: `NearEarthObject`, `CloseApproach`, `NEODatabase`, `NEOExplorerFacade`.

**لماذا:** واجهة عامة واضحة للاستخدام البرمجي (غير الـCLI)، مع إخفاء التفاصيل الداخلية.

---

## خريطة الاعتمادات (من يستورد من)

```
__main__ ─▶ cli ─▶ facade ─▶ extract ─▶ models
                 │        └─▶ database ─▶ models
                 │        │           └─▶ filters ─▶ models
                 │        └─▶ filters
                 ├─▶ display ─▶ models
                 ├─▶ write ─▶ models
                 └─▶ filters, models
```

- الاتجاه أحادي (بلا دورات).
- `models` في القاع لا يستورد أي طبقة.
- `cli` في القمة يعرف `facade` (+ أدوات العرض/التصدير/الفلاتر).

## نصيحة للقراءة الأولى
ابدأ بـ`models.py` (تفهم البيانات)، ثم `extract.py` (كيف تُبنى)، ثم `database.py` (كيف تُربَط وتُستعلَم)، ثم `filters.py` (كيف تُصفّى)، ثم `facade.py` و`cli.py` (كيف تُستخدَم). للتشغيل الحيّ راجع `README.md`.
