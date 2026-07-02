import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from meeting_common import make_fail, make_pass, make_skip, find_keywords, build_evidence, collect_location_sources, build_conflict_evidence, normalize_text

RULE_META = {'id': 'rule_01', 'name': '会议地点是否位于明令禁止风景名胜区', 'category': '会议地点', 'level': 'warning'}

FORBIDDEN = ['八达岭', '十三陵', '承德避暑山庄', '外八庙', '五台山', '太湖', '普陀山', '黄山', '九华山', '武夷山', '庐山', '泰山', '嵩山', '武当山', '武陵源', '张家界', '白云山', '桂林漓江', '三亚热带海滨', '峨眉山', '乐山大佛', '九寨沟', '黄龙', '黄果树', '西双版纳', '华山']

def evaluate(context):
    sources = collect_location_sources(context)
    text_sources = [source for source in sources if normalize_text(source.get('value')) not in ('0', '0.0')]
    if not text_sources:
        if sources:
            return make_pass('rule_01', RULE_META['name'], '会议地点未命中禁止风景名胜区关键词。')
        return make_skip('rule_01', RULE_META['name'], '会议地点字段', build_evidence(field='meetingLocation'))
    risky = []
    for source in text_sources:
        hits = find_keywords(source.get('value'), FORBIDDEN)
        if hits:
            risky.append({**source, 'hits': hits})
    values = {normalize_text(source.get('value')) for source in text_sources if normalize_text(source.get('value'))}
    conflict = len(values) > 1
    if risky:
        location = '；'.join(f"{item.get('source')}={item.get('value')}" for item in risky)
        evidence = build_conflict_evidence('meetingLocation', text_sources)
        evidence['hits'] = [{'source': item.get('source'), 'value': item.get('value'), 'hits': item.get('hits')} for item in risky]
        evidence['hasConflict'] = conflict
        prefix = '会议地点来源存在冲突，且' if conflict else ''
        return make_fail('rule_01', RULE_META['name'], f'{prefix}会议地点疑似位于禁止召开会议的风景名胜区：{location}', '请核对页面地点与会议通知 OCR 地点，必要时补充说明或调整会议地点。', evidence)
    return make_pass('rule_01', RULE_META['name'], '会议地点未命中禁止风景名胜区关键词。')
