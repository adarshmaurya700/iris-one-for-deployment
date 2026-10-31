"""Portable catalog metadata and application instructions. Seeds are not live proof."""
import json
from datetime import datetime, timezone, timedelta


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def today_in_india():
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def json_value(value, default=None):
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value or 'null') or (default if default is not None else [])
    except (ValueError, TypeError):
        return default if default is not None else []


GUIDES = {
    'airtel': {
        'primary': ('Buddy4Study Bharti Airtel Portal', 'https://www.buddy4study.com/page/Bharti-Airtel-Scholarship'),
        'secondary': ('Bharti Airtel Foundation', 'https://bhartiairtelfoundation.org/bharti-airtel-scholarship'),
        'rules': 'https://www.buddy4study.com/page/Bharti-Airtel-Scholarship#guidelines',
        'steps': [
            ('Visit the official application portal', 'Open the Buddy4Study Bharti Airtel page and confirm that the current cycle is accepting applications.'),
            ('Register and complete student verification', 'Sign in or register. Complete the identity or eKYC checks requested by the official portal.'),
            ('Enter academic and financial details', 'Enter Class 12 marks, entrance rank, institution and parental income. Cached criteria: at least 60% marks, income up to INR 8 lakh and a top-50 NIRF engineering institution; confirm the current rules.'),
            ('Upload mandatory documents', 'Prepare Aadhaar, admission letter, fee structure, Class 12 marksheet, entrance scorecard, parent income certificate or ITR, bank statements and a Statement of Purpose (SOP), as requested by the portal.'),
            ('Review and submit', 'Read the non-duplication terms, preview the form and save its acknowledgement. Track the application in IRIS.'),
        ],
        'documents': ['Aadhaar / identity proof', 'Admission letter and fee structure', 'Class 12 marksheet', 'Entrance scorecard', 'Parent income certificate / ITR', 'Bank statements', 'Statement of Purpose (SOP)'],
    },
    'delhi-mcm': {
        'primary': ('Delhi e-District Citizen Portal', 'https://edistrict.delhigovt.nic.in'),
        'secondary': ('MyScheme government information', 'https://www.myscheme.gov.in/schemes/mcmlfas'),
        'rules': 'https://edistrict.delhigovt.nic.in',
        'steps': [
            ('Register on Delhi e-District', 'Open Citizen Corner and complete registration using the identity details requested by the portal.'),
            ('Complete the MCM application', 'Find the current Merit-cum-Means scheme and enter your enrollment details for the participating Delhi state university.'),
            ('Upload the relevant income proof', 'Cached categories: NFSS card for a 100% waiver; SDM income certificate up to INR 2.5 lakh for 50%; parent ITR up to INR 6 lakh for 25%. Confirm current-year categories and requirements.'),
            ('Submit the hard copy and Annexure-A', 'Where required, print the application, attach the signed non-duplication affidavit and submit it to the college nodal officer.'),
        ],
        'documents': ['Delhi domicile certificate', 'Admission / enrollment proof', 'Class 12 marksheet', 'NFSS card / SDM income certificate / parent ITR (applicable category)', 'Signed Annexure-A non-duplication affidavit', 'Bank account details'],
    },
    'adobe-insider': {
        'primary': ('Adobe student portal', 'https://www.adobe.com/creativecloud/buy/students.html'),
        'secondary': ('Adobe Creative Campus', 'https://www.adobe.com/education/creativecampus.html'),
        'steps': [
            ('Verify student status', 'Open Adobe’s official student page and check the current price, regional availability and eligibility. Verify enrollment with the requested email or student ID.'),
            ('Check program access', 'If an Insider or campus cohort is offered through your institution, complete its official application and describe your creative interests.'),
            ('Activate the available benefits', 'Review the actual offer and any payment or renewal terms before activating access. Student discounts do not guarantee a free Creative Cloud subscription.'),
        ],
        'documents': ['Institutional email', 'Current student ID / enrollment proof'],
    },
    'gemini-student': {
        'primary': ('Google One student offer', 'https://one.google.com/ai-student'),
        'secondary': ('Google Cloud for students', 'https://cloud.google.com/edu/students'),
        'steps': [
            ('Open the official student offer', 'Sign in with your personal Google account and check whether an offer is currently available in your country.'),
            ('Complete student verification', 'Use the verification service and enrollment evidence requested by Google. Institutional email alone may not qualify.'),
            ('Review and activate', 'Confirm the displayed price, trial duration, payment requirements and renewal terms. Activate only if the official offer meets your needs.'),
        ],
        'documents': ['Student enrollment proof', 'Google account', 'Identity / age evidence if requested'],
    },
}


def verification_state(opp):
    """Derive public truth at read time, even when the scheduler is stopped."""
    from runtime_config import mode
    status = opp.get('verification_status') or 'SEEDED_CACHE'
    deadline = opp.get('deadline_iso') or opp.get('deadline') or ''
    checked = opp.get('last_verified_at') or ''
    fresh = False
    if checked:
        try:
            timestamp = datetime.fromisoformat(checked.replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            fresh = 0 <= age <= 12 * 3600
        except (ValueError, TypeError):
            pass
    if deadline and deadline < today_in_india().isoformat():
        status = 'EXPIRED'
    elif status == 'VERIFIED_LIVE' and not fresh:
        status = 'PREVIOUSLY_VERIFIED' if checked else 'VERIFICATION_PENDING'
    elif status == 'CACHE_ONLY' and checked:
        status = 'PREVIOUSLY_VERIFIED'
    if mode() == 'demo' and status == 'VERIFIED_LIVE':
        status = 'PREVIOUSLY_VERIFIED'
    channels = json_value(opp.get('application_channels_json'))
    channels = [{**item, 'verified': status == 'VERIFIED_LIVE' and bool(item.get('verified')),
                 'badge': 'Apply Live' if status == 'VERIFIED_LIVE' and item.get('verified') else 'Open'} for item in channels if isinstance(item, dict)]
    return {'verification_status': status, 'is_live_verified': status == 'VERIFIED_LIVE',
            'application_channels_json': json.dumps(channels),
            'data_provenance': 'reference_fixture' if not checked else 'previous_live_observation',
            'is_simulated': mode() == 'demo'}


def application_metadata(opp):
    gates = json_value(opp.get('eligibility_json'), {})
    guide = GUIDES.get(opp.get('slug'), {})
    primary = guide.get('primary', (opp.get('source_portal') or opp.get('organization') or 'Official portal', opp.get('source_url') or opp.get('url', '')))
    secondary = guide.get('secondary')
    steps = guide.get('steps', [
        ('Check the official program page', 'Confirm that the current application window is open and read the official eligibility and terms.'),
        ('Prepare your profile and documents', 'Register or sign in and prepare the evidence listed below. Follow the current official instructions.'),
        ('Review, submit and track', 'Review the application, submit it on the official portal and retain the acknowledgement. Use IRIS to track your progress.'),
    ])
    channels = [{'id': 1, 'name': primary[0], 'url': primary[1], 'badge': 'Open', 'verified': False}]
    if secondary:
        channels.append({'id': 2, 'name': secondary[0], 'url': secondary[1], 'badge': 'Open', 'verified': False})
    states = gates.get('allowed_states') or ['All India']
    tiers = ' '.join(gates.get('academic_tiers') or []).lower()
    income = gates.get('max_family_income_lpa')
    return {
        'provider': opp.get('organization', ''), 'benefit_summary': opp.get('financial_value_label') or opp.get('amount', ''),
        'academic_tier': 'ALL' if '12th' in tiers and 'ug' in tiers else 'TIER_1_SCHOOL' if 'school' in tiers else 'TIER_2_UG_PG',
        'amount_inr': opp.get('estimated_value_inr', 0), 'deadline_iso': opp.get('deadline', ''),
        'location_state': ', '.join(states), 'min_marks_pct': gates.get('min_marks_percentage') or 0,
        'max_family_income_inr': int(income * 100000) if income is not None else 99999999,
        'nirf_top_50_required': int(opp.get('slug') == 'airtel'),
        'is_exclusive_tuition_grant': int(bool(gates.get('is_exclusive_tuition_grant'))),
        'apply_url': primary[1], 'secondary_url': secondary[1] if secondary else '',
        'rules_pdf_url': guide.get('rules', ''),
        'how_to_apply_steps_json': json.dumps([{'step': i + 1, 'title': title, 'detail': detail} for i, (title, detail) in enumerate(steps)]),
        'required_documents_json': json.dumps(guide.get('documents', gates.get('mandatory_documents') or ['Student ID / enrollment proof', 'Program-specific evidence requested by the official portal'])),
        'application_channels_json': json.dumps(channels),
        'skills_tags_json': json.dumps([s.strip() for s in (opp.get('required_skills') or opp.get('tags') or '').split(',') if s.strip()]),
    }
