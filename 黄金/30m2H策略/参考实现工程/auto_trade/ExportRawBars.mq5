//+------------------------------------------------------------------+
//|                                        ExportRawBars.mq5           |
//| 导出 XAUUSDm M30 最近100根bar的 OHLCV + SMA5/13/55 用于对比Python |
//+------------------------------------------------------------------+
#property strict

void OnStart()
{
   string symbol = "XAUUSDm";
   ENUM_TIMEFRAMES tf = PERIOD_M30;
   
   int h_sma5  = iMA(symbol, tf, 5,  0, MODE_SMMA, PRICE_CLOSE);
   int h_sma13 = iMA(symbol, tf, 13, 0, MODE_SMMA, PRICE_CLOSE);
   int h_sma55 = iMA(symbol, tf, 55, 0, MODE_SMMA, PRICE_CLOSE);
   
   string path = "mt5_raw_bars_compare.csv";
   int f = FileOpen(path, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(f == INVALID_HANDLE) { Print("Cannot open file"); return; }
   
   FileWrite(f, "time", "open", "high", "low", "close", "volume", "sma5", "sma13", "sma55");
   
   int bars = 200;  // First 200 bars
   for(int i = bars-1; i >= 0; i--)
   {
      datetime t = iTime(symbol, tf, i);
      double o = iOpen(symbol, tf, i);
      double h = iHigh(symbol, tf, i);
      double l = iLow(symbol, tf, i);
      double c = iClose(symbol, tf, i);
      long   v = iVolume(symbol, tf, i);
      
      double buf5[1], buf13[1], buf55[1];
      CopyBuffer(h_sma5,  0, i, 1, buf5);
      CopyBuffer(h_sma13, 0, i, 1, buf13);
      CopyBuffer(h_sma55, 0, i, 1, buf55);
      
      FileWrite(f, TimeToString(t), o, h, l, c, v, buf5[0], buf13[0], buf55[0]);
   }
   
   FileClose(f);
   Print("Exported ", bars, " bars to ", path);
   
   IndicatorRelease(h_sma5);
   IndicatorRelease(h_sma13);
   IndicatorRelease(h_sma55);
}
