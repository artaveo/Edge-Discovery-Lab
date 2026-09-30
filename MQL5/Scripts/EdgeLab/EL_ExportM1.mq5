//+------------------------------------------------------------------+
//|                                                  EL_ExportM1.mq5 |
//| Edge Discovery Lab - Phase F1 M1 export (roadmap Section 1).      |
//|                                                                  |
//| Writes one gzip CSV per year to MQL5\Files\EdgeLab\data\          |
//|   xauusd_m1_<YYYY>.csv.gz                                        |
//|   columns: time,open,high,low,close,tick_volume,spread_pts       |
//|   time = broker server time "YYYY-MM-DD HH:MM:SS" (bar open)     |
//| and manifest.json (SHA-256, rows, first/last bar, symbol spec,   |
//| server, terminal build, export time).                            |
//|                                                                  |
//| DATA DISCIPLINE: F1 may only export 2019-01-01 .. 2022-12-31.    |
//| The script refuses any other year and never writes a bar dated   |
//| 2023-01-01 or later.                                             |
//+------------------------------------------------------------------+
#property copyright   "Edge Discovery Lab"
#property version     "1.00"
#property description "F1 M1 export (2019-2022 only) with manifest"
#property script_show_inputs

input string InpSymbol   = "XAUUSD";          // Symbol
input int    InpYearFrom = 2019;              // First year (>= 2019)
input int    InpYearTo   = 2022;              // Last year (<= 2022)
input string InpOutDir   = "EdgeLab\\data";   // Folder under MQL5\Files

#define EL_MIN_YEAR 2019
#define EL_MAX_YEAR 2022          // F1: never export 2023 or later
#define EL_MAX_RETRY 40

uint g_crc_table[256];

//+------------------------------------------------------------------+
//| CRC-32 (IEEE 802.3), as required by the gzip trailer             |
//+------------------------------------------------------------------+
void CrcInit()
  {
   const uint poly = (uint)0xEDB88320;
   for(int n = 0; n < 256; n++)
     {
      uint c = (uint)n;
      for(int k = 0; k < 8; k++)
        {
         if((c & 1) != 0)
            c = poly ^ (c >> 1);
         else
            c = c >> 1;
        }
      g_crc_table[n] = c;
     }
  }

uint Crc32(const uchar &buf[], const int len)
  {
   uint c = (uint)0xFFFFFFFF;
   for(int i = 0; i < len; i++)
      c = g_crc_table[(int)((c ^ (uint)buf[i]) & 0xFF)] ^ (c >> 8);
   return(c ^ (uint)0xFFFFFFFF);
  }

//+------------------------------------------------------------------+
//| helpers                                                          |
//+------------------------------------------------------------------+
string IsoTime(const datetime t)
  {
   string s = TimeToString(t, TIME_DATE | TIME_SECONDS);   // 2019.01.02 01:00:00
   StringReplace(s, ".", "-");
   return(s);
  }

string HexBytes(const uchar &b[])
  {
   string s = "";
   int n = ArraySize(b);
   for(int i = 0; i < n; i++)
      s += StringFormat("%02x", b[i]);
   return(s);
  }

string JsonEscape(const string v)
  {
   string s = v;
   StringReplace(s, "\\", "\\\\");
   StringReplace(s, "\"", "\\\"");
   return(s);
  }

datetime YearStart(const int year)
  {
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year;
   d.mon = 1;
   d.day = 1;
   return(StructToTime(d));
  }

datetime MonthStart(const int year, const int mon)
  {
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year + (mon - 1) / 12;
   d.mon = (mon - 1) % 12 + 1;
   d.day = 1;
   return(StructToTime(d));
  }

void AppendUtf8(uchar &data[], int &used, const string block)
  {
   uchar tmp[];
   int n = StringToCharArray(block, tmp, 0, WHOLE_ARRAY, CP_UTF8);
   if(n <= 1)
      return;
   n -= 1;                                  // drop the terminating zero
   if(used + n > ArraySize(data) && ArrayResize(data, used + n, 8 * 1024 * 1024) < 0)
     {
      Print("ERROR: out of memory while building the CSV");
      return;
     }
   ArrayCopy(data, tmp, used, 0, n);
   used += n;
  }

bool CopyChunk(const string sym, const datetime from, const datetime to, MqlRates &rates[])
  {
   for(int attempt = 0; attempt < EL_MAX_RETRY; attempt++)
     {
      ResetLastError();
      int n = CopyRates(sym, PERIOD_M1, from, to, rates);
      if(n > 0)
         return(true);
      PrintFormat("  CopyRates %s..%s returned %d (error %d), retry %d", IsoTime(from), IsoTime(to), n,
                  GetLastError(), attempt + 1);
      Sleep(500);
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| Export one year. Returns the manifest entry (JSON) or "" on error|
//+------------------------------------------------------------------+
string ExportYear(const string sym, const int year, const int digits, const string dir)
  {
   const datetime limit = YearStart(EL_MAX_YEAR + 1);         // 2023-01-01 00:00 (hard guard)
   const datetime y0 = YearStart(year);
   const datetime y1 = YearStart(year + 1);
   uchar data[];
   if(ArrayResize(data, 0, 32 * 1024 * 1024) < 0)
      return("");
   int used = 0;
   AppendUtf8(data, used, "time,open,high,low,close,tick_volume,spread_pts\n");

   long rows = 0;
   datetime first_bar = 0, last_bar = 0, prev = 0;
   long dropped = 0;
   for(int m = 1; m <= 12; m++)
     {
      datetime from = MonthStart(year, m);
      datetime to = MonthStart(year, m + 1) - 1;
      MqlRates rates[];
      if(!CopyChunk(sym, from, to, rates))
        {
         PrintFormat("ERROR: no M1 data for %s %04d-%02d. Is the history loaded and 'Max bars in chart' unlimited?",
                     sym, year, m);
         return("");
        }
      int n = ArraySize(rates);
      string block = "";
      for(int i = 0; i < n; i++)
        {
         datetime t = rates[i].time;
         if(t < y0 || t >= y1 || t >= limit)
            continue;
         if(prev != 0 && t <= prev)
           {
            dropped++;
            continue;
           }
         prev = t;
         if(first_bar == 0)
            first_bar = t;
         last_bar = t;
         rows++;
         block += IsoTime(t) + "," +
                  DoubleToString(rates[i].open, digits) + "," +
                  DoubleToString(rates[i].high, digits) + "," +
                  DoubleToString(rates[i].low, digits) + "," +
                  DoubleToString(rates[i].close, digits) + "," +
                  IntegerToString(rates[i].tick_volume) + "," +
                  IntegerToString(rates[i].spread) + "\n";
         if((i & 1023) == 1023)
           {
            AppendUtf8(data, used, block);
            block = "";
           }
        }
      AppendUtf8(data, used, block);
      PrintFormat("  %04d-%02d: %d bars", year, m, n);
     }
   if(rows == 0)
     {
      PrintFormat("ERROR: year %d has no rows", year);
      return("");
     }
   if(ArrayResize(data, used) != used)
      return("");

   // --- deflate with the terminal, wrap as gzip (RFC 1952)
   uchar key[];
   uchar packed[];
   int plen = CryptEncode(CRYPT_ARCH_ZIP, data, key, packed);
   if(plen <= 0)
     {
      PrintFormat("ERROR: CryptEncode(CRYPT_ARCH_ZIP) failed, error %d", GetLastError());
      return("");
     }
   // round trip check of the terminal's own format
   uchar check[];
   int clen = CryptDecode(CRYPT_ARCH_ZIP, packed, key, check);
   if(clen != used || ArrayCompare(check, data, 0, 0, used) != 0)
     {
      PrintFormat("ERROR: compression round trip failed (%d vs %d bytes)", clen, used);
      return("");
     }
   // CRYPT_ARCH_ZIP may return a zlib stream (RFC 1950: 2-byte header + deflate + adler32)
   // or raw deflate; gzip needs raw deflate.
   int start = 0, dlen = plen;
   int cmf = (int)packed[0], flg = (int)packed[1];
   if(plen > 6 && (cmf & 0x0F) == 8 && (cmf >> 4) <= 7 && (flg & 0x20) == 0 && ((cmf << 8) | flg) % 31 == 0)
     {
      start = 2;
      dlen = plen - 6;
     }
   uint crc = Crc32(data, used);
   uchar gz[];
   if(ArrayResize(gz, 10 + dlen + 8) != 10 + dlen + 8)
      return("");
   gz[0] = 0x1f; gz[1] = 0x8b; gz[2] = 8; gz[3] = 0;          // magic, deflate, no flags
   gz[4] = 0; gz[5] = 0; gz[6] = 0; gz[7] = 0;                // mtime 0 (reproducible)
   gz[8] = 0; gz[9] = 255;                                    // xfl, OS unknown
   ArrayCopy(gz, packed, 10, start, dlen);
   uint isize = (uint)used;
   for(int b = 0; b < 4; b++)
     {
      gz[10 + dlen + b] = (uchar)((crc >> (8 * b)) & 0xFF);
      gz[14 + dlen + b] = (uchar)((isize >> (8 * b)) & 0xFF);
     }

   uchar digest[];
   if(CryptEncode(CRYPT_HASH_SHA256, gz, key, digest) != 32)
     {
      Print("ERROR: SHA-256 failed");
      return("");
     }
   string lsym = sym;
   StringToLower(lsym);
   string name = StringFormat("%s_m1_%04d.csv.gz", lsym, year);
   int h = FileOpen(dir + "\\" + name, FILE_WRITE | FILE_BIN);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("ERROR: cannot open %s (error %d)", name, GetLastError());
      return("");
     }
   uint written = FileWriteArray(h, gz, 0, ArraySize(gz));
   FileClose(h);
   if((int)written != ArraySize(gz))
     {
      PrintFormat("ERROR: wrote %u of %d bytes to %s", written, ArraySize(gz), name);
      return("");
     }
   PrintFormat("%s: %I64d rows, %s .. %s, %d bytes (csv %d), dropped %I64d non-increasing",
               name, rows, IsoTime(first_bar), IsoTime(last_bar), ArraySize(gz), used, dropped);
   return(StringFormat("  {\"file\": \"%s\", \"year\": %d, \"rows\": %I64d, \"first_bar\": \"%s\", "
                       "\"last_bar\": \"%s\", \"sha256\": \"%s\", \"bytes\": %d, \"csv_bytes\": %d, "
                       "\"crc32\": \"%08x\", \"dropped_non_increasing\": %I64d}",
                       name, year, rows, IsoTime(first_bar), IsoTime(last_bar), HexBytes(digest),
                       ArraySize(gz), used, crc, dropped));
  }

//+------------------------------------------------------------------+
//| Script entry point                                               |
//+------------------------------------------------------------------+
void OnStart()
  {
   if(InpYearFrom < EL_MIN_YEAR || InpYearTo > EL_MAX_YEAR || InpYearFrom > InpYearTo)
     {
      PrintFormat("REFUSED: F1 may only export %d..%d (asked %d..%d). Nothing written.",
                  EL_MIN_YEAR, EL_MAX_YEAR, InpYearFrom, InpYearTo);
      return;
     }
   if(!SymbolSelect(InpSymbol, true))
     {
      PrintFormat("ERROR: symbol %s not available", InpSymbol);
      return;
     }
   CrcInit();
   const int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   const double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   const double contract = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE);
   const string server = AccountInfoString(ACCOUNT_SERVER);
   const string company = AccountInfoString(ACCOUNT_COMPANY);
   const int build = (int)TerminalInfoInteger(TERMINAL_BUILD);
   const int maxbars = (int)TerminalInfoInteger(TERMINAL_MAXBARS);
   PrintFormat("EL_ExportM1: %s %d..%d, digits %d, point %s, contract %s, server %s, build %d, max bars %d",
               InpSymbol, InpYearFrom, InpYearTo, digits, DoubleToString(point, digits),
               DoubleToString(contract, 2), server, build, maxbars);

   string parts[];
   int np = StringSplit(InpOutDir, '\\', parts);
   string sub = "";
   bool folder_ok = true;
   for(int i = 0; i < np; i++)
     {
      sub += (i == 0 ? "" : "\\") + parts[i];
      folder_ok = folder_ok && FolderCreate(sub);
     }
   if(!folder_ok)
     {
      PrintFormat("ERROR: cannot create MQL5\\Files\\%s (error %d)", InpOutDir, GetLastError());
      return;
     }

   string entries = "";
   long total = 0;
   for(int y = InpYearFrom; y <= InpYearTo; y++)
     {
      if(y > EL_MAX_YEAR)
         break;                                 // unreachable by the check above; kept as a guard
      string e = ExportYear(InpSymbol, y, digits, InpOutDir);
      if(e == "")
        {
         Print("EXPORT FAILED - manifest not written. Fix the error and run again.");
         return;
        }
      entries += (entries == "" ? "" : ",\n") + e;
      int p = StringFind(e, "\"rows\": ");
      if(p >= 0)
         total += StringToInteger(StringSubstr(e, p + 8, 12));
     }

   string js = "{\n";
   js += "  \"schema\": \"edgelab.export.v1\",\n";
   js += "  \"symbol\": \"" + JsonEscape(InpSymbol) + "\",\n";
   js += "  \"server\": \"" + JsonEscape(server) + "\",\n";
   js += "  \"company\": \"" + JsonEscape(company) + "\",\n";
   js += "  \"terminal_build\": " + IntegerToString(build) + ",\n";
   js += "  \"digits\": " + IntegerToString(digits) + ",\n";
   js += "  \"point\": " + DoubleToString(point, digits) + ",\n";
   js += "  \"contract_size\": " + DoubleToString(contract, 2) + ",\n";
   js += "  \"timeframe\": \"M1\",\n";
   js += "  \"time\": \"broker server time, bar open, YYYY-MM-DD HH:MM:SS\",\n";
   js += "  \"columns\": [\"time\", \"open\", \"high\", \"low\", \"close\", \"tick_volume\", \"spread_pts\"],\n";
   js += "  \"year_from\": " + IntegerToString(InpYearFrom) + ",\n";
   js += "  \"year_to\": " + IntegerToString(InpYearTo) + ",\n";
   js += "  \"exported_at_server\": \"" + IsoTime(TimeTradeServer()) + "\",\n";
   js += "  \"exported_at_utc\": \"" + IsoTime(TimeGMT()) + "\",\n";
   js += "  \"total_rows\": " + IntegerToString(total) + ",\n";
   js += "  \"files\": [\n" + entries + "\n  ]\n}\n";

   int h = FileOpen(InpOutDir + "\\manifest.json", FILE_WRITE | FILE_BIN);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("ERROR: cannot write manifest.json (error %d)", GetLastError());
      return;
     }
   uchar buf[];
   int n = StringToCharArray(js, buf, 0, WHOLE_ARRAY, CP_UTF8);
   uint mw = FileWriteArray(h, buf, 0, n - 1);
   FileClose(h);
   if((int)mw != n - 1)
     {
      PrintFormat("ERROR: manifest.json incomplete (%u of %d bytes)", mw, n - 1);
      return;
     }
   PrintFormat("EL_ExportM1 DONE: %I64d rows in %d files -> MQL5\\Files\\%s", total,
               InpYearTo - InpYearFrom + 1, InpOutDir);
  }
//+------------------------------------------------------------------+
