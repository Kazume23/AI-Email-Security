import hashlib
import json
import urllib.request
import pandas as pd
from ai_email_security.config import project_path


if __name__ == '__main__':
    folder = project_path('data') / 'v030'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'external.csv'
    url = 'https://zenodo.org/records/13474746/files/Phishing_validation_emails.csv?download=1'
    if not target.exists():
        urllib.request.urlretrieve(url, target)
    frame = pd.read_csv(target)
    print(frame.shape, frame.columns.tolist())
    print(frame.head(4).to_json(orient='records'))
    print(frame.iloc[:, -1].value_counts().to_dict())
    info = {'url': url, 'license': 'CC-BY-4.0', 'origin': 'mixed real and generated, per publisher',
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    (folder / 'source.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    second = folder / 'independent.jsonl'
    revision = '1d7c404463d5dab2d1aa1d9f0807ba372703fd09'
    second_url = f'https://raw.githubusercontent.com/SunnyThakur25/Phishing-Benign-Email-Dataset-Short-Version-/{revision}/phishing%20and%20benign%20email%20dataset.jsonl'
    if not second.exists():
        urllib.request.urlretrieve(second_url, second)
    print('Independent:', pd.read_json(second, lines=True).shape)
    info = {'url': second_url, 'license': 'MIT', 'revision': revision,
            'sha256': hashlib.sha256(second.read_bytes()).hexdigest(), 'origin': 'curated examples, real-world provenance not established'}
    (folder / 'independent-source.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
