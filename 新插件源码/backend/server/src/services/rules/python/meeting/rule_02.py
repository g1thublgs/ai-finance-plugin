import pathlib
import re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from meeting_common import make_pass, make_warning, to_text, build_evidence, collect_payment_sources, build_conflict_evidence

RULE_META = {'id': 'rule_02', 'name': '未使用公务卡结算提示', 'category': '公务卡结算', 'level': 'warning'}

def looks_person_name(name):
    text = re.sub(r'\s+', '', to_text(name))
    org_words = ['公司', '酒店', '宾馆', '税务局', '中心', '单位', '服务部', '有限公司', '学校', '学院', '饭店', '餐厅', '会务', '会议']
    return bool(re.match(r'^[\u4e00-\u9fa5]{2,4}$', text)) and not any(k in text for k in org_words)

def evaluate(context):
    rows = collect_payment_sources(context)
    if not rows:
        return make_warning('rule_02', RULE_META['name'], '未提取到财务信息-收款人信息，需人工复核是否使用公务卡结算。', evidence=build_evidence(field='payments'))
    issues = []
    for row in rows:
        payee = to_text(row.get('payeeName'))
        card_amount = row.get('cardAmount')
        card_time = to_text(row.get('cardTime'))
        if payee and looks_person_name(payee) and not card_time and (card_amount is None or card_amount <= 0):
            issues.append({'payee': payee, 'source': row.get('source'), 'sourceGroup': row.get('sourceGroup')})
    if issues:
        payees = [item['payee'] for item in issues]
        has_page_org = any(row.get('sourceGroup') == 'page' and row.get('payeeName') and not looks_person_name(row.get('payeeName')) for row in rows)
        has_ocr_person = any(item.get('sourceGroup') == 'ocr' for item in issues)
        prefix = '页面付款信息与 OCR 付款凭证存在冲突，且' if has_page_org and has_ocr_person else ''
        return make_warning('rule_02', RULE_META['name'], f'{prefix}收款人疑似个人且无刷卡时间及刷卡金额：{"、".join(payees)}', '请核对是否应使用公务卡结算或补充公务卡消费明细。', build_evidence(payees=issues, conflictEvidence=build_conflict_evidence('payeeName', rows)))
    return make_pass('rule_02', RULE_META['name'], '未发现疑似个人收款且缺少公务卡信息的记录。')
