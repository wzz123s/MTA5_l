//+------------------------------------------------------------------+
//| ProbeCalendar_EA.mq5 - discover struct fields via compile errors |
//+------------------------------------------------------------------+
#property strict

int OnInit()
  {
   MqlCalendarValue v;
   MqlCalendarEvent e;
   int p1  = (int)v.currency;        // CANDIDATE v.currency
   int p2  = (int)v.importance;      // CANDIDATE v.importance
   int p3  = (int)v.date_utc;        // CANDIDATE v.date_utc
   int p4  = (int)v.event_type;      // CANDIDATE v.event_type
   int p5  = (int)v.sector;          // CANDIDATE v.sector
   int p6  = (int)v.country;         // CANDIDATE v.country
   int p7  = (int)v.unit;            // CANDIDATE v.unit
   int p8  = (int)v.frequency;       // CANDIDATE v.frequency
   int p9  = (int)v.time_mode;       // CANDIDATE v.time_mode
   int p10 = (int)v.timezone;        // CANDIDATE v.timezone
   int p11 = (int)v.source;          // CANDIDATE v.source
   int p12 = (int)v.description;     // CANDIDATE v.description
   int p13 = (int)v.name;            // CANDIDATE v.name
   int p14 = (int)v.importance_lvl;  // CANDIDATE v.importance_lvl
   int q1  = (int)e.event_type;      // CANDIDATE e.event_type
   int q2  = (int)e.country;         // CANDIDATE e.country
   int q3  = (int)e.currency;        // CANDIDATE e.currency
   int q4  = (int)e.sector;          // CANDIDATE e.sector
   int q5  = (int)e.frequency;       // CANDIDATE e.frequency
   int q6  = (int)e.time_mode;       // CANDIDATE e.time_mode
   int q7  = (int)e.timezone;        // CANDIDATE e.timezone
   int q8  = (int)e.unit;            // CANDIDATE e.unit
   int q9  = (int)e.source;          // CANDIDATE e.source
   int q10 = (int)e.url_name;        // CANDIDATE e.url_name
   int q11 = (int)e.description;     // CANDIDATE e.description
   int q12 = (int)e.country_id;      // CANDIDATE e.country_id
   int q13 = (int)e.importance;      // CANDIDATE e.importance
   int q14 = (int)e.date_utc;        // CANDIDATE e.date_utc
   PrintFormat("probe %d %d %d %d %d %d %d %d %d %d %d %d %d %d | %d %d %d %d %d %d %d %d %d %d %d %d %d %d",
               p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p13,p14,
               q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13,q14);
   PrintFormat("sizeof value=%d event=%d", sizeof(MqlCalendarValue), sizeof(MqlCalendarEvent));
   return INIT_FAILED;
  }
void OnTick() { }
