import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from meeting_common import make_fail, make_pass, make_skip, meeting_days, summary, to_text, build_evidence

RULE_META = {'id': 'rule_06', 'name': '会议天数超标准提示', 'category': '会议天数', 'level': 'warning'}
LIMITS = {'二类': 3, '三类': 3, '四类': 2.5}

def recognized_category(context):
    text = to_text((summary(context) or {}).get('meetingCategory') or (summary(context) or {}).get('category'))
    if '二类' in text:
        return '二类'
    if '三类' in text:
        return '三类'
    if '四类' in text:
        return '四类'
    return ''

def evaluate(context):
    category = recognized_category(context)
    days = meeting_days(context)
    if not category:
        return make_skip('rule_06', RULE_META['name'], '可识别的会议类别字段，无法判断会议天数标准', build_evidence(days=days))
    if not days:
        return make_skip('rule_06', RULE_META['name'], '会议天数字段', build_evidence(category=category))
    limit = LIMITS[category]
    if days > limit:
        return make_fail('rule_06', RULE_META['name'], f'{category}会议天数 {days} 天，大于规定上限 {limit} 天。', '请核对会议通知时间、报到返程安排及天数计算口径。', build_evidence(category=category, days=days, limit=limit))
    return make_pass('rule_06', RULE_META['name'], f'{category}会议天数 {days} 天未超过上限 {limit} 天。')
