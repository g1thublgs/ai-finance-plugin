import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from meeting_common import get_summary_amount_info, make_pass, make_warning, build_evidence, build_conflict_evidence

RULE_META = {'id': 'rule_13', 'name': '住宿费为零但存在场地租金提示', 'category': '费用结构', 'level': 'warning'}

def evaluate(context):
    accommodation_info = get_summary_amount_info(context, 'accommodationAmount')
    venue_info = get_summary_amount_info(context, 'venueRentAmount')
    accommodation = accommodation_info.get('value')
    venue = venue_info.get('highRiskValue') if venue_info.get('hasConflict') else venue_info.get('value')
    accommodation_sources = accommodation_info.get('sources') or []
    zero_accommodation_sources = [source for source in accommodation_sources if source.get('amount') is not None and source.get('amount') <= 0.01]
    if not accommodation_info.get('hasValue') and venue_info.get('hasValue') and venue > 0.01:
        return make_warning('rule_13', RULE_META['name'], f'未采集到住宿费字段，场地租金为 {venue:.2f} 元。', '请人工复核住宿费是否确为 0 或未填，避免因字段缺失误判。', build_evidence(accommodationSource=accommodation_info.get('source'), venueRentAmount=venue, venueSource=venue_info.get('source')))
    if accommodation_info.get('hasConflict') and zero_accommodation_sources and venue_info.get('hasValue') and venue > 0.01:
        return make_warning('rule_13', RULE_META['name'], f'页面/OCR住宿费或场地租金存在冲突，且存在住宿费为 0 元、场地租金为 {venue:.2f} 元的来源。', '请核对住宿费是否确为 0、场地租金填报是否合理，避免按页面值静默通过。', build_evidence(accommodationEvidence=build_conflict_evidence('accommodationAmount', accommodation_sources), venueEvidence=build_conflict_evidence('venueRentAmount', venue_info.get('sources'))))
    if accommodation <= 0.01 and venue > 0.01:
        return make_warning('rule_13', RULE_META['name'], f'住宿费为 0 元，场地租金为 {venue:.2f} 元。', '请核对会议是否实际发生住宿、场地租金填报是否合理。', build_evidence(accommodationAmount=accommodation, accommodationSource=accommodation_info.get('source'), venueRentAmount=venue, venueSource=venue_info.get('source'), accommodationEvidence=build_conflict_evidence('accommodationAmount', accommodation_sources), venueEvidence=build_conflict_evidence('venueRentAmount', venue_info.get('sources'))))
    return make_pass('rule_13', RULE_META['name'], '未发现住宿费为 0 且场地租金不为 0 的情况。')
