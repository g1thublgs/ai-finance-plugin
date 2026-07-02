import datetime
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from meeting_common import date_range, make_pass, make_skip, make_warning, summary, build_evidence, collect_date_sources, build_conflict_evidence

RULE_META = {'id': 'rule_10', 'name': '会议时间是否为节假日或周末', 'category': '会议时间', 'level': 'warning'}
HOLIDAYS = {
    datetime.date(2026, 1, 1),
    datetime.date(2026, 2, 16), datetime.date(2026, 2, 17), datetime.date(2026, 2, 18), datetime.date(2026, 2, 19), datetime.date(2026, 2, 20), datetime.date(2026, 2, 21), datetime.date(2026, 2, 22),
    datetime.date(2026, 4, 4), datetime.date(2026, 4, 5), datetime.date(2026, 4, 6),
    datetime.date(2026, 5, 1), datetime.date(2026, 5, 2), datetime.date(2026, 5, 3), datetime.date(2026, 5, 4), datetime.date(2026, 5, 5),
    datetime.date(2026, 6, 19), datetime.date(2026, 6, 20), datetime.date(2026, 6, 21),
    datetime.date(2026, 9, 25), datetime.date(2026, 9, 26), datetime.date(2026, 9, 27),
    datetime.date(2026, 10, 1), datetime.date(2026, 10, 2), datetime.date(2026, 10, 3), datetime.date(2026, 10, 4), datetime.date(2026, 10, 5), datetime.date(2026, 10, 6), datetime.date(2026, 10, 7),
}

def evaluate(context):
    s = summary(context)
    date_sources = collect_date_sources(context)
    days = []
    for source in date_sources:
        start = source.get('startDate')
        end = source.get('endDate')
        if start and end:
            days.extend(date_range(start.isoformat(), end.isoformat()))
    if not days:
        days = date_range(s.get('startDate') or s.get('meetingDate'), s.get('endDate'))
    if not days:
        return make_skip('rule_10', RULE_META['name'], '会议开始日期和结束日期字段', build_evidence(meetingDate=s.get('meetingDate')))
    days = sorted(set(days))
    date_values = {f"{source.get('startDate')}~{source.get('endDate')}" for source in date_sources if source.get('startDate')}
    has_conflict = len(date_values) > 1
    holiday_years = {d.year for d in HOLIDAYS}
    details = [
        {
            'date': d.isoformat(),
            'weekday': d.weekday() + 1,
            'isWeekend': d.weekday() >= 5,
            'isHoliday': d in HOLIDAYS,
            'holidaySource': '内置2026节假日表' if d.year in holiday_years else '节假日数据未配置',
        }
        for d in days
    ]
    unconfigured = sorted({d.year for d in days if d.year not in holiday_years})
    if unconfigured:
        return make_warning('rule_10', RULE_META['name'], f'会议日期年份 {unconfigured} 未配置法定节假日数据，需人工复核。', '系统仅可稳定判断周末；未配置年份的法定节假日需人工确认。', build_evidence(dates=details))
    hits = [item for item in details if item['isWeekend'] or item['isHoliday']]
    if hits:
        prefix = '页面/OCR日期存在冲突，且' if has_conflict else ''
        return make_warning('rule_10', RULE_META['name'], f'{prefix}会议时间包含周末或法定节假日：{"、".join(item["date"] for item in hits)}。', '请核对会议安排是否确需在周末或节假日召开，并补充审批说明。', build_evidence(dates=details, hits=hits, dateEvidence=build_conflict_evidence('meetingDate', date_sources)))
    if has_conflict:
        return make_warning('rule_10', RULE_META['name'], '页面/OCR日期存在冲突，需人工复核会议时间是否涉及周末或节假日。', '请核对页面会议日期与会议通知、计划、审批 OCR 日期是否一致。', build_evidence(dates=details, dateEvidence=build_conflict_evidence('meetingDate', date_sources)))
    return make_pass('rule_10', RULE_META['name'], '会议时间未命中周末或已维护法定节假日。')
