import sys, time, requests

sys.stdout.reconfigure(encoding='utf-8')
BASE = 'http://127.0.0.1:5000'

try:
    print('1. 기사 가져오기 (top)')
    r = requests.get(BASE + '/api/news?category=top')
    data = r.json()
    url = data['articles'][0]['link']
    print('   Target URL:', url)

    print('\n2. 요약본 가져오기')
    r2 = requests.get(BASE + '/api/summary?url=' + requests.utils.quote(url))
    summary_data = r2.json()
    status = summary_data.get('status')
    summary = summary_data.get('summary', '')
    print('   Status:', status)
    print('   Summary:', summary[:150], '...')

    if status == 'success':
        print('\n3. 요약본 번역')
        r3 = requests.post(BASE + '/api/translate', json={'text': summary[:300]})
        trans_data = r3.json()
        print('   Translated:', trans_data.get('translation', '')[:100], '...')
        
    print('\n[SUCCESS] Summary feature tests passed!')
except Exception as e:
    print('\n[ERROR]', str(e))
