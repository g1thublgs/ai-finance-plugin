import datetime
import re


EPSILON = 0.01


def to_text(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value).strip()


def has_meaningful_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list)):
        return bool(value)
    return True


def normalize_text(value):
    return re.sub(r'\s+', '', to_text(value))


def get_nested(data, paths, default=None):
    if isinstance(paths, str):
        paths = [paths]
    for path in paths or []:
        cur = data
        ok = True
        for part in str(path).split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur.get(part)
            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            else:
                ok = False
                break
        if ok and cur not in (None, ''):
            return cur
    return default


def to_number(value, default=0):
    if value in (None, ''):
        return default
    if isinstance(value, (int, float)):
        return value
    text = to_text(value).replace(',', '').replace('，', '').replace('￥', '').replace('¥', '').replace('元', '')
    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return default
    try:
        return float(match.group(0))
    except Exception:
        return default


CN_DIGITS = {
    '零': 0, '〇': 0, '○': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '壹': 1, '贰': 2,
    '貳': 2, '叁': 3, '參': 3, '肆': 4, '伍': 5, '陆': 6, '陸': 6,
    '柒': 7, '捌': 8, '玖': 9,
}
CN_UNITS = {'十': 10, '拾': 10, '百': 100, '佰': 100, '千': 1000, '仟': 1000}
CN_BIG_UNITS = {'万': 10000, '萬': 10000, '亿': 100000000, '億': 100000000}


def parse_chinese_integer(text):
    text = normalize_text(text)
    if not text:
        return None
    total = 0
    section = 0
    number = 0
    seen = False
    for ch in text:
        if ch in CN_DIGITS:
            number = CN_DIGITS[ch]
            seen = True
        elif ch in CN_UNITS:
            unit = CN_UNITS[ch]
            if number == 0:
                number = 1
            section += number * unit
            number = 0
            seen = True
        elif ch in CN_BIG_UNITS:
            unit = CN_BIG_UNITS[ch]
            section += number
            if section == 0:
                section = 1
            total += section * unit
            section = 0
            number = 0
            seen = True
        else:
            return None
    if not seen:
        return None
    return total + section + number


def parse_chinese_amount(value):
    text = normalize_text(value)
    if not text:
        return None
    text = text.replace('人民币', '').replace('金额', '').replace('大写', '')
    text = text.replace('圆', '元').replace('正', '整')
    allowed = ''.join(CN_DIGITS.keys()) + ''.join(CN_UNITS.keys()) + ''.join(CN_BIG_UNITS.keys())
    match = re.search(f'([{re.escape(allowed)}]+)元(?:整)?(?:(零|[{re.escape(allowed)}]+)角)?(?:(零|[{re.escape(allowed)}]+)分)?', text)
    if not match:
        return None
    integer = parse_chinese_integer(match.group(1))
    if integer is None:
        return None
    amount = float(integer)
    if match.group(2) and match.group(2) != '零':
        jiao = parse_chinese_integer(match.group(2))
        if jiao is None:
            return None
        amount += jiao / 10
    if match.group(3) and match.group(3) != '零':
        fen = parse_chinese_integer(match.group(3))
        if fen is None:
            return None
        amount += fen / 100
    return amount


def parse_amount(value):
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = to_text(value).replace(',', '').replace('，', '').replace('￥', '').replace('¥', '')
    text = text.replace('人民币', '').replace('元', '').replace('圆', '')
    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return parse_chinese_amount(value)
    try:
        return float(match.group(0))
    except Exception:
        return None


def to_int(value, default=0):
    try:
        return int(round(to_number(value, default)))
    except Exception:
        return default


def parse_date(value):
    text = to_text(value)
    if not text:
        return None
    text = text.replace('年', '-').replace('月', '-').replace('日', '').replace('/', '-').replace('.', '-')
    match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if not match:
        return None
    try:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except Exception:
        return None


def parse_date_range_text(value, year_hint=None):
    text = to_text(value)
    if not text:
        return (None, None)
    explicit = re.findall(r'(\d{4})[年\-/\.](\d{1,2})[月\-/\.](\d{1,2})日?', text)
    if len(explicit) > 1:
        start = datetime.date(int(explicit[0][0]), int(explicit[0][1]), int(explicit[0][2]))
        last = explicit[-1]
        return (start, datetime.date(int(last[0]), int(last[1]), int(last[2])))
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日?\s*(?:至|到|-|—|~)\s*(?:(\d{4})年)?(?:(\d{1,2})月)?(\d{1,2})日?', text)
    if match:
        year = int(match.group(1))
        start = datetime.date(year, int(match.group(2)), int(match.group(3)))
        end_year = int(match.group(4) or year)
        end_month = int(match.group(5) or match.group(2))
        end = datetime.date(end_year, end_month, int(match.group(6)))
        return (start, end)
    match = re.search(r'(\d{1,2})月(\d{1,2})日?\s*(?:至|到|-|—|~)\s*(\d{1,2})月(\d{1,2})日?', text)
    if match and year_hint:
        start = datetime.date(int(year_hint), int(match.group(1)), int(match.group(2)))
        end = datetime.date(int(year_hint), int(match.group(3)), int(match.group(4)))
        return (start, end)
    single = parse_date(text)
    return (single, single)


def date_range(start, end):
    if start and not end and re.search(r'(至|到|-|—|~)', to_text(start)):
        start_date, end_date = parse_date_range_text(start)
    else:
        start_date = parse_date(start)
        end_date = parse_date(end) or start_date
    if not start_date and start:
        start_date, end_date = parse_date_range_text(start)
    if start_date and not end_date:
        end_date = start_date
    if not start_date:
        return []
    if end_date < start_date:
        return [start_date]
    days = []
    cur = start_date
    while cur <= end_date:
        days.append(cur)
        cur += datetime.timedelta(days=1)
    return days


def date_diff_days(start, end):
    dates = date_range(start, end)
    return len(dates) if dates else 0


def summary(context):
    return context.get('summary') or (context.get('prefillData') or {}).get('summary') or {}


def get_summary(context):
    return summary(context)


def get_page_fields(context):
    s = summary(context)
    page = s.get('pageFields') or {}
    return page if isinstance(page, dict) else {}


def get_page_expense(context):
    page = get_page_fields(context)
    return {
        'mealAmount': page.get('mealAmount'),
        'accommodationAmount': page.get('accommodationAmount'),
        'venueRentAmount': page.get('venueRentAmount'),
        'applyAmount': page.get('applyAmount'),
        'totalAmount': page.get('totalAmount'),
    }


def ocr_items(context):
    items = context.get('ocrItems') or (context.get('prefillData') or {}).get('ocrItems') or []
    return items if isinstance(items, list) else []


def collect_ocr_items(context):
    return ocr_items(context)


def records(context):
    rows = context.get('records') or (context.get('prefillData') or {}).get('records') or []
    return rows if isinstance(rows, list) else []


def evidence_map(context):
    value = context.get('evidence') or (context.get('prefillData') or {}).get('evidence') or {}
    return value if isinstance(value, dict) else {}


def payments(context):
    rows = context.get('payments') or context.get('paymentInfoList') or summary(context).get('payments') or []
    if not rows:
        rows = [item for item in ocr_items(context) if doc_type(item) == 'paymentProof']
    return rows if isinstance(rows, list) else []


def doc_type(item):
    return to_text((item or {}).get('recognizeType') or (item or {}).get('docType') or (item or {}).get('type'))


def has_doc_type(data, doc_types):
    wanted = set(doc_types if isinstance(doc_types, list) else [doc_types])
    if any(doc_type(item) in wanted for item in ocr_items(data)):
        return True
    s = summary(data)
    bool_fields = {
        'meetingNotice': 'hasMeetingNotice',
        'meetingApproval': 'hasMeetingApproval',
        'meetingPlan': 'hasMeetingPlan',
        'attendanceList': 'hasAttendanceList',
        'meetingSettlement': 'hasSettlement',
        'accommodationList': 'hasAccommodationList',
        'normalInvoice': 'hasInvoice',
        'paymentProof': 'hasPaymentProof',
    }
    return any(s.get(bool_fields.get(item, '')) for item in wanted)


def get_bool_doc_flag(context, doc_type_name):
    return has_doc_type(context, doc_type_name)


def items_by_type(context, *types):
    wanted = set(types)
    return [item for item in ocr_items(context) if doc_type(item) in wanted]


def get_first_value(context, candidate_paths):
    roots = {
        'summary': summary(context),
        'pageFields': get_page_fields(context),
        'context': context,
    }
    for path in candidate_paths or []:
        path = to_text(path)
        if not path:
            continue
        parts = path.split('.')
        root = roots.get(parts[0])
        if root is not None:
            value = get_nested(root, '.'.join(parts[1:]), None) if len(parts) > 1 else root
        else:
            value = get_nested(context, path, None)
        if value not in (None, ''):
            return {'value': value, 'source': path}
    return {'value': '', 'source': ''}


def get_amount_with_source(context, candidate_paths):
    found = get_first_value(context, candidate_paths)
    amount = parse_amount(found.get('value'))
    if amount is None:
        return {'value': 0, 'hasValue': False, 'source': found.get('source'), 'raw': found.get('value')}
    return {'value': amount, 'hasValue': True, 'source': found.get('source'), 'raw': found.get('value')}


def get_text_with_source(context, candidate_paths):
    found = get_first_value(context, candidate_paths)
    return {'value': to_text(found.get('value')), 'source': found.get('source'), 'raw': found.get('value')}


def all_text(data, doc_types=None):
    wanted = set(doc_types or [])
    chunks = []
    for item in ocr_items(data):
        if wanted and doc_type(item) not in wanted:
            continue
        chunks.append(to_text(item.get('rawText')))
        chunks.append(to_text(item.get('meetingName')))
        chunks.append(to_text(item.get('location')))
        chunks.append(to_text(item.get('attendeeScope')))
        chunks.append(to_text(item.get('organizer')))
        for key in ['itemsDetail', 'details', 'detailRows']:
            rows = item.get(key) or []
            if isinstance(rows, list):
                for row in rows:
                    chunks.append(' '.join(to_text(v) for v in (row or {}).values()))
    return '\n'.join(chunks)


def text_sources(data, doc_types=None):
    wanted = set(doc_types or [])
    sources = []
    for idx, item in enumerate(ocr_items(data)):
        dtype = doc_type(item)
        if wanted and dtype not in wanted:
            continue
        file_name = to_text(item.get('sourceFileName') or item.get('fileName'))
        chunks = [item.get('rawText'), item.get('meetingName'), item.get('location'), item.get('attendeeScope'), item.get('organizer'), item.get('sellerName'), item.get('payeeName')]
        for key in ['itemsDetail', 'details', 'detailRows']:
            rows = item.get(key) or []
            if isinstance(rows, list):
                for row in rows:
                    chunks.append(' '.join(to_text(v) for v in (row or {}).values()))
        text = '\n'.join(to_text(part) for part in chunks if to_text(part))
        if text:
            sources.append({'index': idx, 'docType': dtype, 'fileName': file_name, 'text': text})
    return sources


def find_keywords(text, keywords):
    compact = normalize_text(text)
    return [kw for kw in keywords if normalize_text(kw) in compact]


def keyword_hits(data, keywords, doc_types=None, exclude_contexts=None):
    hits = []
    seen = set()
    excludes = [normalize_text(item) for item in (exclude_contexts or [])]
    for source in text_sources(data, doc_types):
        compact = normalize_text(source['text'])
        for kw in keywords:
            nkw = normalize_text(kw)
            if not nkw or nkw not in compact:
                continue
            raw_text = source['text']
            pos = normalize_text(raw_text).find(nkw)
            context = raw_text[:120] if pos < 0 else raw_text[max(0, pos - 30):pos + len(kw) + 30]
            if any(ex in normalize_text(context) for ex in excludes):
                continue
            key = (source['docType'], source['fileName'], kw, normalize_text(context))
            if key in seen:
                continue
            seen.add(key)
            hits.append({**source, 'keyword': kw, 'context': context})
    return hits


PAGE_TEXT_FIELDS = [
    'expenseDetail', 'feeDetail', 'settlementDetail', 'accommodationRemark',
    'accommodationDetail', 'remark', 'reason', 'description', 'meetingReason',
    'settlementRemark', 'feeDescription', 'BZ', 'SQ_SY', 'QTFY',
]


def _source_entry(value, source, field='', source_group='page', doc_type_name='', file_name='', raw_text=''):
    return {
        'value': value,
        'text': to_text(value),
        'source': source,
        'field': field,
        'sourceGroup': source_group,
        'docType': doc_type_name,
        'fileName': to_text(file_name),
        'rawText': to_text(raw_text)[:200],
    }


def _append_value_source(sources, value, source, field='', source_group='page', doc_type_name='', file_name='', raw_text=''):
    if has_meaningful_value(value):
        sources.append(_source_entry(value, source, field, source_group, doc_type_name, file_name, raw_text))


def collect_text_sources(context, purpose=None):
    sources = []
    s = summary(context)
    page = get_page_fields(context)
    fields = list(PAGE_TEXT_FIELDS)
    if purpose == 'accommodation':
        fields = ['accommodationDetail', 'accommodationRemark', 'expenseDetail', 'feeDetail', 'settlementDetail', 'remark', 'description', 'BZ', 'QTFY']
    for field in fields:
        _append_value_source(sources, s.get(field), f'summary.{field}', field)
        _append_value_source(sources, page.get(field), f'summary.pageFields.{field}', field)
    for idx, item in enumerate(ocr_items(context)):
        dtype = doc_type(item)
        file_name = item.get('sourceFileName') or item.get('fileName')
        raw = item.get('rawText')
        chunks = [raw, item.get('meetingName'), item.get('location'), item.get('sellerName'), item.get('payeeName')]
        _append_value_source(sources, '\n'.join(to_text(part) for part in chunks if to_text(part)), f'ocrItems[{idx}].rawText', 'rawText', 'ocr', dtype, file_name, raw)
        for key in ['itemsDetail', 'details', 'detailRows']:
            rows = item.get(key) or []
            if isinstance(rows, list):
                for row_idx, row in enumerate(rows):
                    if isinstance(row, dict):
                        for field in ['name', 'description', 'itemName', 'feeName']:
                            _append_value_source(sources, row.get(field), f'ocrItems[{idx}].{key}[{row_idx}].{field}', field, 'ocr', dtype, file_name, raw)
                    else:
                        _append_value_source(sources, row, f'ocrItems[{idx}].{key}[{row_idx}]', key, 'ocr', dtype, file_name, raw)
    return sources


def keyword_hits_from_sources(sources, keywords, exclude_contexts=None):
    hits = []
    seen = set()
    excludes = [normalize_text(item) for item in (exclude_contexts or [])]
    for source in sources or []:
        text = to_text(source.get('text') or source.get('value'))
        compact = normalize_text(text)
        if not compact:
            continue
        for kw in keywords:
            nkw = normalize_text(kw)
            if not nkw or nkw not in compact:
                continue
            pos = compact.find(nkw)
            context = text[:120] if pos < 0 else text[max(0, pos - 30):pos + len(kw) + 30]
            if any(ex in normalize_text(context) for ex in excludes):
                continue
            key = (source.get('source'), kw, normalize_text(context))
            if key in seen:
                continue
            seen.add(key)
            hits.append({
                'keyword': kw,
                'context': context,
                'source': source.get('source'),
                'sourceGroup': source.get('sourceGroup'),
                'docType': source.get('docType'),
                'fileName': source.get('fileName'),
            })
    return hits


def collect_location_sources(context):
    sources = []
    s = summary(context)
    page = get_page_fields(context)
    for field in ['meetingLocation', 'location']:
        _append_value_source(sources, s.get(field), f'summary.{field}', field)
        _append_value_source(sources, page.get(field), f'summary.pageFields.{field}', field)
    for idx, item in enumerate(ocr_items(context)):
        dtype = doc_type(item)
        if dtype and dtype not in ('meetingNotice', 'meetingPlan', 'meetingApproval', 'other'):
            continue
        file_name = item.get('sourceFileName') or item.get('fileName')
        raw = item.get('rawText')
        for field in ['location', 'meetingLocation', 'address']:
            _append_value_source(sources, item.get(field), f'ocrItems[{idx}].{field}', field, 'ocr', dtype, file_name, raw)
        raw_text = to_text(raw)
        if raw_text:
            match = re.search(r'(?:会议地点|地点|会场)[:：\s]*([^\n。；;，,]{2,80})', raw_text)
            _append_value_source(sources, match.group(1) if match else raw_text, f'ocrItems[{idx}].rawText', 'rawText', 'ocr', dtype, file_name, raw)
    return sources


def _parse_date_source_value(value):
    text = to_text(value)
    if not text:
        return (None, None, 0)
    start, end = parse_date_range_text(text)
    if not start:
        start = parse_date(text)
        end = start
    days = len(date_range(start.isoformat(), end.isoformat())) if start and end else 0
    return (start, end, days)


def collect_date_sources(context):
    sources = []
    s = summary(context)
    page = get_page_fields(context)
    for root_name, root in [('summary', s), ('summary.pageFields', page)]:
        raw_days = root.get('meetingDays') or root.get('HYTS')
        parsed_days = parse_amount(raw_days)
        if parsed_days is not None and parsed_days > 0:
            sources.append({**_source_entry(raw_days, f'{root_name}.meetingDays', 'meetingDays'), 'days': parsed_days, 'startDate': None, 'endDate': None})
        start_raw = root.get('startDate')
        end_raw = root.get('endDate')
        meeting_raw = root.get('meetingDate')
        if has_meaningful_value(start_raw) or has_meaningful_value(end_raw):
            dates = date_range(start_raw or meeting_raw, end_raw)
            if dates:
                sources.append({**_source_entry(f'{start_raw or ""} {end_raw or ""}'.strip(), f'{root_name}.startDate/endDate', 'dateRange'), 'days': len(dates), 'startDate': dates[0], 'endDate': dates[-1]})
        if has_meaningful_value(meeting_raw):
            start, end, days = _parse_date_source_value(meeting_raw)
            if days:
                sources.append({**_source_entry(meeting_raw, f'{root_name}.meetingDate', 'meetingDate'), 'days': days, 'startDate': start, 'endDate': end})
    for idx, item in enumerate(ocr_items(context)):
        dtype = doc_type(item)
        if dtype not in ('meetingNotice', 'meetingPlan', 'meetingApproval'):
            continue
        file_name = item.get('sourceFileName') or item.get('fileName')
        raw = item.get('rawText')
        if has_meaningful_value(item.get('startDate')) or has_meaningful_value(item.get('endDate')):
            dates = date_range(item.get('startDate') or item.get('meetingDate'), item.get('endDate'))
            if dates:
                sources.append({**_source_entry(f'{item.get("startDate") or ""} {item.get("endDate") or ""}'.strip(), f'ocrItems[{idx}].startDate/endDate', 'dateRange', 'ocr', dtype, file_name, raw), 'days': len(dates), 'startDate': dates[0], 'endDate': dates[-1]})
        for field in ['meetingDate', 'rawText']:
            start, end, days = _parse_date_source_value(item.get(field))
            if days:
                sources.append({**_source_entry(item.get(field), f'ocrItems[{idx}].{field}', field, 'ocr', dtype, file_name, raw), 'days': days, 'startDate': start, 'endDate': end})
    return sources


def collect_amount_sources(context, field_names):
    if isinstance(field_names, str):
        field_names = [field_names]
    sources = []
    s = summary(context)
    page = get_page_fields(context)
    for field in field_names:
        for root_name, root in [('summary', s), ('summary.pageFields', page)]:
            if field in root:
                amount = parse_amount(root.get(field))
                sources.append({**_source_entry(root.get(field), f'{root_name}.{field}', field), 'amount': amount, 'hasValue': amount is not None})
    for idx, item in enumerate(ocr_items(context)):
        dtype = doc_type(item)
        file_name = item.get('sourceFileName') or item.get('fileName')
        raw = item.get('rawText')
        for field in field_names:
            if field in item:
                amount = parse_amount(item.get(field))
                sources.append({**_source_entry(item.get(field), f'ocrItems[{idx}].{field}', field, 'ocr', dtype, file_name, raw), 'amount': amount, 'hasValue': amount is not None})
        for row_key in ['itemsDetail', 'details', 'detailRows']:
            rows = item.get(row_key) or []
            if not isinstance(rows, list):
                continue
            for row_idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                name = to_text(row.get('name') or row.get('itemName') or row.get('description') or row.get('feeName'))
                amount = parse_amount(row.get('amount') or row.get('totalAmount'))
                if any(field in ('mealAmount', 'HSF') for field in field_names) and '伙食' in name:
                    sources.append({**_source_entry(row.get('amount'), f'ocrItems[{idx}].{row_key}[{row_idx}]', 'mealAmount', 'ocr', dtype, file_name, raw), 'amount': amount, 'hasValue': amount is not None})
                if any(field in ('accommodationAmount', 'ZSF') for field in field_names) and '住宿' in name:
                    sources.append({**_source_entry(row.get('amount'), f'ocrItems[{idx}].{row_key}[{row_idx}]', 'accommodationAmount', 'ocr', dtype, file_name, raw), 'amount': amount, 'hasValue': amount is not None})
                if any(field in ('venueRentAmount', 'venueAmount', 'CDF') for field in field_names) and ('场地' in name or '场租' in name or '租金' in name):
                    sources.append({**_source_entry(row.get('amount'), f'ocrItems[{idx}].{row_key}[{row_idx}]', 'venueRentAmount', 'ocr', dtype, file_name, raw), 'amount': amount, 'hasValue': amount is not None})
    return sources


def collect_payment_sources(context):
    sources = []
    rows = [('summary.payments', idx, row, 'page', '', '') for idx, row in enumerate(payments(context)) if isinstance(row, dict)]
    rows.extend(('ocrItems', idx, item, 'ocr', doc_type(item), item.get('rawText')) for idx, item in enumerate(ocr_items(context)) if doc_type(item) == 'paymentProof')
    seen = set()
    for root, idx, row, source_group, dtype, raw in rows:
        payee = row.get('payee') or row.get('skrmc') or row.get('payeeName') or row.get('收款人名称')
        card_raw = row.get('cardAmount') or row.get('BX_JE') or row.get('刷卡金额')
        card_time = row.get('cardTime') or row.get('GWKHKSJ') or row.get('刷卡时间')
        key = (root, idx, to_text(payee), to_text(card_raw), to_text(card_time))
        if key in seen:
            continue
        seen.add(key)
        if has_meaningful_value(payee) or has_meaningful_value(card_raw) or has_meaningful_value(card_time):
            sources.append({
                **_source_entry(payee, f'{root}[{idx}]', 'payeeName', source_group, dtype, row.get('sourceFileName') or row.get('fileName'), raw),
                'payeeName': to_text(payee),
                'cardAmount': parse_amount(card_raw),
                'cardAmountRaw': card_raw,
                'cardTime': to_text(card_time),
            })
    return sources


def collect_fee_structure_sources(context):
    return {
        'accommodationAmount': collect_amount_sources(context, ['accommodationAmount', 'ZSF']),
        'mealAmount': collect_amount_sources(context, ['mealAmount', 'HSF']),
        'venueRentAmount': collect_amount_sources(context, ['venueRentAmount', 'venueAmount', 'CDF']),
        'totalAmount': collect_amount_sources(context, ['SQ_JE', 'invoiceAmount', 'applyAmount', 'totalAmount']),
    }


def detect_conflicts(sources, field_name, normalize_func=None):
    values = []
    for source in sources or []:
        raw = source.get(field_name)
        if raw is None:
            raw = source.get('value')
        value = normalize_func(raw) if normalize_func else raw
        if value in (None, ''):
            continue
        values.append((value, source))
    normalized = {to_text(value) for value, _ in values}
    return {'hasConflict': len(normalized) > 1, 'values': values, 'sources': [source for _, source in values]}


def pick_high_risk_amount(sources):
    valid = [source for source in (sources or []) if source.get('amount') is not None]
    if not valid:
        return {'value': 0, 'hasValue': False, 'sources': sources or []}
    best = max(valid, key=lambda item: item.get('amount') or 0)
    return {'value': best.get('amount'), 'hasValue': True, 'source': best.get('source'), 'raw': best.get('value'), 'sources': valid}


def build_conflict_evidence(field_name, sources):
    return {
        'field': field_name,
        'sources': [
            build_evidence(
                value=source.get('value'),
                amount=source.get('amount'),
                days=source.get('days'),
                source=source.get('source'),
                sourceGroup=source.get('sourceGroup'),
                docType=source.get('docType'),
                fileName=source.get('fileName'),
                rawText=to_text(source.get('rawText'))[:120],
            )
            for source in (sources or [])
        ],
    }


def get_amount(data, paths, default=0):
    return to_number(get_nested(data, paths, default), default)


def get_summary_amount(data, field, default=0):
    return to_number(summary(data).get(field), default)


def get_summary_amount_info(data, field):
    field_aliases = {
        'mealAmount': ['mealAmount', 'HSF'],
        'accommodationAmount': ['accommodationAmount', 'ZSF'],
        'venueRentAmount': ['venueRentAmount', 'venueAmount', 'CDF'],
        'invoiceAmount': ['SQ_JE', 'invoiceAmount', 'applyAmount', 'totalAmount'],
    }
    sources = collect_amount_sources(data, field_aliases.get(field, [field]))
    valid = [source for source in sources if source.get('amount') is not None]
    if not valid:
        return {'value': 0, 'hasValue': False, 'source': '', 'raw': '', 'sources': sources}
    page_valid = [source for source in valid if source.get('sourceGroup') == 'page']
    best = max(page_valid or valid, key=lambda item: item.get('amount') or 0)
    all_values = {round(source.get('amount') or 0, 2) for source in valid}
    has_evidence = bool(evidence_map(data).get(field))
    return {
        'value': best.get('amount') if best.get('amount') is not None else 0,
        'hasValue': bool(valid) and (abs(best.get('amount') or 0) > EPSILON or has_evidence or best.get('amount') == 0),
        'source': best.get('source'),
        'raw': best.get('value'),
        'sources': valid,
        'hasConflict': len(all_values) > 1,
        'highRiskValue': max(source.get('amount') or 0 for source in valid),
    }


def is_zero_or_blank(value):
    return value in (None, '') or abs(to_number(value, 0)) <= EPSILON


def is_positive(value):
    return to_number(value, 0) > EPSILON


def build_evidence(**kwargs):
    return {k: v for k, v in kwargs.items() if v not in (None, '')}


def issue(category, description, suggestion, severity='warning', evidence=None):
    return {
        'category': category,
        'description': description,
        'suggestion': suggestion,
        'severity': severity,
        'evidence': evidence or {},
    }


def result(rule_id, name, passed, summary_text, issues=None):
    tagged = []
    for item in issues or []:
        tagged.append({**item, 'ruleId': rule_id, 'ruleName': name})
    return {'passed': passed, 'issues': tagged, 'summary': summary_text}


def make_pass(rule_id, name, summary_text='未发现明显问题。', evidence=None):
    return result(rule_id, name, True, summary_text, [])


def make_warning(rule_id, name, description, suggestion='请人工复核。', evidence=None, category=None):
    return result(rule_id, name, False, description, [issue(category or name, description, suggestion, 'warning', evidence)])


def make_fail(rule_id, name, description, suggestion='请核实并补充说明。', evidence=None, category=None):
    return result(rule_id, name, False, description, [issue(category or name, description, suggestion, 'error', evidence)])


def make_skip(rule_id, name, missing, evidence=None):
    text = f'缺少{missing}，需人工复核。'
    return result(rule_id, name, False, text, [issue(name, text, '请补充页面字段或附件识别结果后重新审核。', 'warning', evidence)])


def meeting_category(data):
    info = meeting_category_info(data)
    return info.get('category', '')


def recognized_meeting_category(data):
    info = meeting_category_info(data)
    if info.get('confidence') in ('explicit', 'high'):
        return info.get('category', '')
    return ''


def category_evidence(data):
    return meeting_category_info(data).get('evidence', {})


def category_confidence(data):
    return meeting_category_info(data).get('confidence', '')


def meeting_category_info(data):
    s = summary(data)
    explicit = to_text(s.get('meetingCategory') or s.get('category'))
    if explicit:
        if '二类' in explicit:
            return {'category': '二类', 'confidence': 'explicit', 'evidence': build_evidence(source='summary.meetingCategory', text=explicit)}
        if '三类' in explicit:
            return {'category': '三类', 'confidence': 'explicit', 'evidence': build_evidence(source='summary.meetingCategory', text=explicit)}
        if '四类' in explicit:
            return {'category': '四类', 'confidence': 'explicit', 'evidence': build_evidence(source='summary.meetingCategory', text=explicit)}
        return {'category': '', 'confidence': 'none', 'evidence': build_evidence(source='summary.meetingCategory', text=explicit)}
    page = get_page_fields(data)
    unit = normalize_text(page.get('reimbursementUnitName') or get_nested(data, ['unitName', 'departmentName'], ''))
    name = normalize_text(s.get('meetingName') or page.get('meetingName') or all_text(data, ['meetingNotice', 'meetingPlan']))
    attendee_scope = normalize_text(all_text(data, ['meetingNotice']))
    evidence = build_evidence(unit=unit, meetingName=name, attendeeScope=attendee_scope[:120])
    if '国家税务总局' in unit and '全国税务工作会议' in name:
        return {'category': '二类', 'confidence': 'high', 'evidence': evidence}
    if ('国家税务总局' in unit and ('各省' in attendee_scope or '计划单列市' in attendee_scope)) or ('省税务局' in unit and ('年度工作会议' in name or '省税务工作会议' in name)):
        return {'category': '三类', 'confidence': 'high', 'evidence': evidence}
    if name or unit or attendee_scope:
        return {'category': '四类', 'confidence': 'low', 'evidence': evidence}
    return {'category': '', 'confidence': 'none', 'evidence': evidence}


def attendee_count(data):
    info = attendee_count_info(data)
    return info.get('count', 0)


def attendee_count_info(data):
    s = summary(data)
    for item in ocr_items(data):
        if doc_type(item) == 'attendanceList':
            names = item.get('names') or item.get('attendees') or []
            if isinstance(names, list) and names:
                normalized = set()
                for row in names:
                    name = row.get('name') if isinstance(row, dict) else row
                    name = normalize_text(name)
                    if name:
                        normalized.add(name)
                if normalized:
                    return {'count': len(normalized), 'source': 'ocr.attendanceList.names', 'evidence': build_evidence(count=len(normalized), source='attendanceList')}
            count = to_int(item.get('count'), 0)
            if count:
                return {'count': count, 'source': 'ocr.attendanceList.count', 'evidence': build_evidence(count=count, source='attendanceList')}
    page_count = to_int(get_page_fields(data).get('attendeeCount'), 0)
    if page_count:
        return {'count': page_count, 'source': 'summary.pageFields.attendeeCount', 'evidence': build_evidence(count=page_count)}
    if to_int(s.get('attendeeCount'), 0):
        return {'count': to_int(s.get('attendeeCount'), 0), 'source': 'summary.attendeeCount', 'evidence': build_evidence(count=to_int(s.get('attendeeCount'), 0))}
    return {'count': 0, 'source': '', 'evidence': {}}


def meeting_days(data):
    info = meeting_days_info(data)
    return info.get('days', 0)


def meeting_days_info(data):
    sources = [source for source in collect_date_sources(data) if source.get('days')]
    if not sources:
        return {'days': 0, 'source': '', 'evidence': {}}
    best = max(sources, key=lambda item: item.get('days') or 0)
    values = {source.get('days') for source in sources}
    return {
        'days': best.get('days'),
        'source': best.get('source'),
        'hasConflict': len(values) > 1,
        'sources': sources,
        'evidence': build_evidence(days=best.get('days'), source=best.get('source'), conflict=len(values) > 1, sources=build_conflict_evidence('meetingDays', sources).get('sources')),
    }


def invoice_amount(data):
    info = invoice_amount_info(data)
    return info.get('value', 0)


def invoice_amount_info(data):
    page_sources = collect_amount_sources(data, ['SQ_JE', 'invoiceAmount', 'applyAmount', 'totalAmount'])
    page_sources = [source for source in page_sources if source.get('sourceGroup') == 'page' and source.get('amount') is not None]
    invoice_sources = []
    total = 0
    seen = set()
    for idx, item in enumerate(ocr_items(data)):
        if doc_type(item) not in ('normalInvoice', 'meetingSettlement'):
            continue
        key = to_text(item.get('invoiceNumber') or item.get('invoiceNo')) or f'idx:{idx}'
        amount = parse_amount(item.get('totalAmount') or item.get('invoiceAmount') or item.get('amount'))
        if amount is None:
            continue
        source = {
            **_source_entry(item.get('totalAmount') or item.get('invoiceAmount') or item.get('amount'), f'ocrItems[{idx}].totalAmount', 'totalAmount', 'ocr', doc_type(item), item.get('sourceFileName') or item.get('fileName'), item.get('rawText')),
            'amount': amount,
            'hasValue': True,
        }
        invoice_sources.append(source)
        if doc_type(item) != 'normalInvoice':
            continue
        if key in seen:
            continue
        seen.add(key)
        total += amount
    sources = list(page_sources)
    if total > EPSILON:
        sources.append({**_source_entry(total, 'ocr.normalInvoice.dedupTotal', 'invoiceAmount', 'ocr'), 'amount': total, 'hasValue': True})
    sources.extend([source for source in invoice_sources if source.get('docType') == 'meetingSettlement'])
    valid = [source for source in sources if source.get('amount') is not None]
    if not valid:
        return {'value': 0, 'hasValue': False, 'sources': sources, 'hasConflict': False}
    best = max(valid, key=lambda item: item.get('amount') or 0)
    values = {round(source.get('amount') or 0, 2) for source in valid}
    return {'value': best.get('amount'), 'hasValue': True, 'source': best.get('source'), 'raw': best.get('value'), 'sources': valid, 'hasConflict': len(values) > 1}
