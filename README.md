# 껄무새 시뮬레이터

"그때 그거 살 걸..."이라는 회한(껄무새)을 정량화하는 macOS 데스크톱 앱.

과거 시점에 특정 자산을 (일시매수 또는 DCA로) 매수했다고 가정했을 때 현재까지의 수익률을 계산하고, 같은 금액으로 벤치마크 자산을 샀을 때와 비교한다.

## 지원 마켓

- **크립토**: Binance (USDT 페어), Upbit (KRW 페어)
- **한국 주식**: KOSPI, KOSDAQ (yfinance, `.KS`/`.KQ`)
- **미국 주식**: NASDAQ, NYSE (yfinance)

## 환경 셋업

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 실행

```bash
python main.py
```

## 테스트

```bash
pytest
pytest --cov=regret/domain
```

## 폴더 구조

```
regret/
├── domain/        # 순수 비즈니스 로직 (Pydantic 모델, 계산)
├── data/          # 외부 데이터 어댑터 (yfinance/binance/upbit) + parquet 캐시
├── persistence/   # Portfolio JSON 저장/불러오기
├── config/        # 마켓별 수수료율, 환경 설정
└── ui/            # PyQt6 + PyQtGraph
```

## 시간대 처리

모든 일자는 tz-naive `date`로 정규화한다.
- 한국 주식·KOSPI/KOSDAQ: KST 일자 기준
- 미국 주식: ET(현지) 일자 기준
- 크립토: **UTC 일자** 기준 (24시간 시장이므로 UTC 자정 기준 캔들을 따름)

## v1 범위 외

- 세금 계산
- 다중 통화 환산 비교
- 복수 포트폴리오 동시 비교
- 실시간 가격 스트리밍
- 매도 시뮬레이션
- 종목 검색/자동완성
