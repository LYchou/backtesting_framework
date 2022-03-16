import backtesting_framework as bf
import datetime

class ma_Strategy(bf.strategy.Strategy):

 
  params = ((ma_month_period,None),)

  def initial(self):
    '''
    策略初始化設定。
    Strategy 物件初始化不要用這個寫 def __init__(self)，
    因為繼承來的內容需要透過def __init__(self)初始化一些東西，避免這些東西被複寫掉。

    所以提供 def initial(self) 對策略作一些初始化。
    '''
    self.ma_period = self.params.ma_month_period*20 # 假設一個月20個交易日

  def pre_next(self):
    '''
    在 self.next() 執行前會先執行這個 method。
    通常用於列印出訊息，用於debug。
    '''
    if self.data_center.notify_orNot:
      print('---pre_next---')
      pending_open_orders = [order_obj.ticker for order_obj in self.data_center.pending_open_orders]
      pending_close_orders = [order_obj.ticker for order_obj in self.data_center.pending_close_orders]
      holded_orders = [order_obj.ticker for order_obj in self.data_center.holded_orders]

      print(f'{self.data_center.date} , cash={self.data_center.cash} , value={self.data_center.value}')
      print('==========')
      print(f'pending_open_orders={pending_open_orders}')
      print(f'pending_close_orders={pending_close_orders}')
      print(f'holded_orders={holded_orders}')


  def next(self):
      '''
      主要用於撰寫交易策略，決定隔日開盤買進賣出。
      '''

      pass


  def after_next(self):
    '''
    在 self.next() 執行後會執行這個 method。
    通常用於列印出訊息，用於debug。
    '''
    if self.data_center.notify_orNot:
      print('---after_next---')
      pending_open_orders = [order_obj.ticker for order_obj in self.data_center.pending_open_orders]
      pending_close_orders = [order_obj.ticker for order_obj in self.data_center.pending_close_orders]
      holded_orders = [order_obj.ticker for order_obj in self.data_center.holded_orders]
      print(f'pending_open_orders={pending_open_orders}')
      print(f'pending_close_orders={pending_close_orders}')
      print(f'holded_orders={holded_orders}')
      print('\n\n')

      
cerebro = bf.cerebro.Cerebro()
cerebro.datas_table = px_data
ma_month_period = 1 # 一個月
cerebro.addstrategy(
    ma_Strategy,
    ma_month_period = ma_month_period
)
cerebro.notify_orNot = False # 設定要不要輸出訊息 (True還會額外輸出成交訊息:成功/margin call ....)
cerebro.close_at_BacktestingEndDate_orNot = True # 是否要在回測最後一天賣出所有部位，持有現金
cerebro.cash = 100000 # 初始資金

cerebro.start_date = datetime.datetime(2017,1,1)   # 回測起始時間
cerebro.end_date = datetime.datetime(2021,11,30)   # 回測結束時間

cerebro.run()
