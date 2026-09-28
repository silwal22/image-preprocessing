# PAN Card Extraction Quality Report

This report is generated from the actual evaluation run and includes dummy-only PAN card samples.

## Accuracy by image quality and config

| image_quality | raw | rotate | brightness | rotate+brightness |
| --- | ---: | ---: | ---: | ---: |
| blurry | 0.000 | 0.000 | 0.000 | 0.000 |
| clean | 1.000 | 1.000 | 1.000 | 1.000 |
| dark | 1.000 | 1.000 | 1.000 | 1.000 |
| rotated | 0.000 | 0.000 | 0.000 | 1.000 |

## Best config per quality bucket

| image_quality | best_config | delta_vs_raw |
| --- | --- | ---: |
| blurry | rotate | 0.000 |
| clean | rotate | 0.000 |
| dark | rotate | 0.000 |
| rotated | rotate+brightness | 1.000 |

## Confidence calibration

- Mean confidence when all fields correct: 0.990
- Mean confidence when any field wrong or missed: 0.486

## Failure list

| sample_id | image_quality | config | field | expected | got | status |
| --- | --- | --- | --- | --- | --- | --- |
| blurry_04 | blurry | raw | full_name | BALJIWAN BATRA | BALWINDER SINGH | wrong |
| blurry_04 | blurry | raw | father_name | NAKUL BHAVSAR | MANOJ BHASIN | wrong |
| blurry_04 | blurry | raw | pan_number | DBESL2117Q | DBDSL2117Q | wrong |
| blurry_04 | blurry | raw | date_of_birth | 19/11/1989 | 15/11/1988 | wrong |
| blurry_04 | blurry | rotate | full_name | BALJIWAN BATRA | BALKRISHNA | wrong |
| blurry_04 | blurry | rotate | father_name | NAKUL BHAVSAR | MANOJ BHAVSAR | wrong |
| blurry_04 | blurry | rotate | pan_number | DBESL2117Q | DBKSL1111Q | wrong |
| blurry_04 | blurry | rotate | date_of_birth | 19/11/1989 | 15/11/1988 | wrong |
| blurry_04 | blurry | brightness | full_name | BALJIWAN BATRA | BALWINDER SINGH | wrong |
| blurry_04 | blurry | brightness | father_name | NAKUL BHAVSAR | MANOJ BHASIN | wrong |
| blurry_04 | blurry | brightness | pan_number | DBESL2117Q | DBDSL2117Q | wrong |
| blurry_04 | blurry | brightness | date_of_birth | 19/11/1989 | 15/11/1988 | wrong |
| blurry_04 | blurry | rotate+brightness | full_name | BALJIWAN BATRA | BALKRISHNA | wrong |
| blurry_04 | blurry | rotate+brightness | father_name | NAKUL BHAVSAR | MANOJ BHAVSAR | wrong |
| blurry_04 | blurry | rotate+brightness | pan_number | DBESL2117Q | DBKSL1111Q | wrong |
| blurry_04 | blurry | rotate+brightness | date_of_birth | 19/11/1989 | 15/11/1988 | wrong |
| rotated_02 | rotated | raw | full_name | HEMANGINI DHINGRA | None | missed |
| rotated_02 | rotated | raw | father_name | WARJAS MERCHANT | None | missed |
| rotated_02 | rotated | raw | pan_number | JUUNG7502R | None | missed |
| rotated_02 | rotated | raw | date_of_birth | 11/10/1998 | None | missed |
| rotated_02 | rotated | rotate | full_name | HEMANGINI DHINGRA | None | missed |
| rotated_02 | rotated | rotate | father_name | WARJAS MERCHANT | None | missed |
| rotated_02 | rotated | rotate | pan_number | JUUNG7502R | None | missed |
| rotated_02 | rotated | rotate | date_of_birth | 11/10/1998 | None | missed |
| rotated_02 | rotated | brightness | full_name | HEMANGINI DHINGRA | None | missed |
| rotated_02 | rotated | brightness | father_name | WARJAS MERCHANT | None | missed |
| rotated_02 | rotated | brightness | pan_number | JUUNG7502R | None | missed |
| rotated_02 | rotated | brightness | date_of_birth | 11/10/1998 | None | missed |

## Analysis (fill in manually)

### What preprocessing helped or hurt

- Fill in with the observed effect of rotate, brightness, and combined preprocessing for each image-quality bucket.

### Where the model still fails

- Fill in with examples of OCR errors, partial-card issues, or inconsistent field extraction.

### Caveats

- Tiny sample size: this study uses a small set of synthetic PAN-card samples.
- Single document template: the cards are all generated from the same style and layout.
- Dummy data only: the card text is synthetic and not tied to real individuals.
