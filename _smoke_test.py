import sys
try:
    import pandas as pd
    print('pandas', pd.__version__)
    df = pd.read_excel('Windsor-20250922.xlsx')
    print('Loaded', len(df), 'rows; columns:', list(df.columns)[:20])
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
