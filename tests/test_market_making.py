import pytest
from market_making import Account, QuoteConfig, quotes
from strategy_research import make_tape, replay, predictive_analysis, run


def test_round_trip_pnl_and_fees():
    a=Account()
    a.fill('BUY',10,100)
    a.fill('SELL',10,101)
    m=a.mark(101)
    assert m['inventory']==0
    assert m['realised_pnl']==10
    assert m['net_pnl']==pytest.approx(9.98)


def test_short_cover_and_position_flip():
    a=Account()
    a.fill('SELL',10,100,0)
    a.fill('BUY',15,98,0)
    assert a.inventory==5
    assert a.average_cost==98
    assert a.realised==20
    assert a.mark(99)['net_pnl']==25


def test_account_identity_with_partial_close():
    a=Account()
    for side,qty,price in [('BUY',10,100),('BUY',10,102),('SELL',5,103),('SELL',30,104),('BUY',8,101)]:
        a.fill(side,qty,price)
        m=a.mark(102)
        assert m['net_pnl']==pytest.approx(m['realised_pnl']+m['unrealised_pnl']-m['fees'])


def test_inventory_skews_quotes_and_limits_size():
    c=QuoteConfig()
    flat=quotes(100,.01,0,c)
    long=quotes(100,.01,100,c)
    assert long[0]<flat[0] and long[1]<flat[1]
    assert long[2]==0
    assert quotes(100,0,-100,c)[3]==0
    assert quotes(100,0,95,c)[2]==5


def test_volatility_widens_spread():
    c=QuoteConfig()
    b,a,*_=quotes(100,.1,0,c)
    b0,a0,*_=quotes(100,0,0,c)
    assert a-b>a0-b0


def test_replay_reproducible_and_risk_bounded():
    tape=make_tape(7,200)
    rows,summary=replay(tape,QuoteConfig())
    assert (rows,summary)==replay(tape,QuoteConfig())
    assert summary['max_inventory']<=100
    assert summary['traded_quantity']>0
    assert summary['net_pnl']==pytest.approx(summary['realised_pnl']+summary['unrealised_pnl']-summary['fees'])


def test_no_future_access():
    tape=make_tape(1,100)
    rows,_=replay(tape,QuoteConfig())
    changed=[dict(e) for e in tape]
    changed[-1]['next_mid']+=10
    other,_=replay(changed,QuoteConfig())
    # Final mark changes, but quotes/fills/inventory cannot depend on that mark.
    assert rows[:-1]==other[:-1]
    for key in ('inventory','cash','fees','spread','imbalance'):
        assert rows[-1][key]==other[-1][key]


def test_chronological_holdout():
    rows,_=replay(make_tape(2,100),QuoteConfig())
    stats=predictive_analysis(rows)
    assert stats['train_rows']==70 and stats['test_rows']==30
    # Holdout targets never affect fitted coefficients.
    altered=[dict(r) for r in rows]
    for r in altered[70:]: r['next_mid_change']+=1
    assert predictive_analysis(altered)['slope']==stats['slope']


def test_report_smoke(tmp_path):
    result=run(tmp_path,seeds=2,steps=30)
    assert result['seeds']==2
    assert (tmp_path/'report.html').exists()


@pytest.mark.parametrize('side,quantity,price',[('X',1,100),('BUY',0,100),('BUY',1,float('nan'))])
def test_invalid_fill(side,quantity,price):
    with pytest.raises(ValueError): Account().fill(side,quantity,price)


def test_drawdown_stop_cancels_quotes():
    tape=[dict(mid=100.,next_mid=90.,side='SELL',quantity=20,bid_depth=50,ask_depth=50),
          dict(mid=90.,next_mid=80.,side='SELL',quantity=20,bid_depth=50,ask_depth=50)]
    rows,summary=replay(tape,QuoteConfig(),max_drawdown=1)
    assert rows[0]['halted']
    assert rows[1]['inventory']==rows[0]['inventory']
    assert summary['halted']
    assert rows[1]['net_pnl']<rows[0]['net_pnl']


def test_wider_quotes_reduce_price_sensitive_fills():
    tape=make_tape(42,300)
    _,narrow=replay(tape,QuoteConfig(half_spread=.015,inventory_skew=0,volatility_multiplier=0))
    _,wide=replay(tape,QuoteConfig(half_spread=.055,inventory_skew=0,volatility_multiplier=0))
    assert narrow['traded_quantity']>wide['traded_quantity']
