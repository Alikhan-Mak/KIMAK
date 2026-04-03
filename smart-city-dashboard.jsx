import { useState, useEffect } from "react";

const DISTRICTS = [
  {
    id: 1, name: "Алматинский", x: 120, y: 80, w: 160, h: 120,
    energy: 87, energyTrend: "+5%",
    incidents: [
      { id: 1, type: "water", severity: "high", desc: "Прорыв трубы на ул. Абая", time: "08:14" },
      { id: 2, type: "electric", severity: "medium", desc: "Перебои с электричеством", time: "09:32" },
    ]
  },
  {
    id: 2, name: "Бостандыкский", x: 290, y: 60, w: 150, h: 140,
    energy: 54, energyTrend: "-2%",
    incidents: [
      { id: 3, type: "heat", severity: "low", desc: "Слабый напор теплоснабжения", time: "07:55" },
    ]
  },
  {
    id: 3, name: "Медеуский", x: 300, y: 210, w: 140, h: 110,
    energy: 72, energyTrend: "+1%",
    incidents: []
  },
  {
    id: 4, name: "Жетысуский", x: 130, y: 210, w: 160, h: 110,
    energy: 93, energyTrend: "+12%",
    incidents: [
      { id: 4, type: "water", severity: "high", desc: "Авария на водопроводе", time: "06:40" },
      { id: 5, type: "road", severity: "high", desc: "Засор канализации", time: "10:01" },
      { id: 6, type: "electric", severity: "medium", desc: "Плановое отключение", time: "11:20" },
    ]
  },
  {
    id: 5, name: "Турксибский", x: 450, y: 140, w: 130, h: 130,
    energy: 61, energyTrend: "0%",
    incidents: [
      { id: 7, type: "road", severity: "low", desc: "Повреждение дороги", time: "09:10" },
    ]
  },
];

const SEVERITY_COLOR = { high: "#ef4444", medium: "#f59e0b", low: "#22c55e" };
const SEVERITY_LABEL = { high: "Высокий", medium: "Средний", low: "Низкий" };
const TYPE_ICON = { water: "💧", electric: "⚡", heat: "🔥", road: "🚧" };

function energyColor(val) {
  if (val >= 85) return "#ef4444";
  if (val >= 70) return "#f59e0b";
  return "#22c55e";
}

function energyOpacity(val) {
  return 0.15 + (val / 100) * 0.55;
}

const AI_SUMMARIES = {
  1: {
    status: "Критично",
    color: "#ef4444",
    what: "Алматинский район перегружен: потребление энергии 87% от нормы, зафиксированы 2 инцидента ЖКХ включая прорыв трубы.",
    severity: "Высокий — требует немедленного вмешательства.",
    action: "Направить аварийную бригаду на ул. Абая. Проверить состояние электросетей до конца дня."
  },
  2: {
    status: "Норма",
    color: "#22c55e",
    what: "Бостандыкский район функционирует стабильно. Потребление энергии 54%, один незначительный инцидент с теплоснабжением.",
    severity: "Низкий — ситуация под контролем.",
    action: "Плановый мониторинг. Уведомить жильцов о слабом напоре теплоснабжения."
  },
  3: {
    status: "Норма",
    color: "#22c55e",
    what: "Медеуский район без инцидентов. Потребление энергии 72% — незначительный рост.",
    severity: "Низкий — штатный режим.",
    action: "Проверить причину роста потребления в следующем цикле мониторинга."
  },
  4: {
    status: "Аварийный",
    color: "#ef4444",
    what: "Жетысуский район в аварийном состоянии: потребление 93%, 3 активных инцидента включая аварию водопровода и засор канализации.",
    severity: "Высокий — множественные критические отказы инфраструктуры.",
    action: "Немедленно активировать протокол аварийного реагирования. Перераспределить нагрузку на соседние районы."
  },
  5: {
    status: "Норма",
    color: "#22c55e",
    what: "Турксибский район в норме. Потребление стабильно 61%, один незначительный дорожный инцидент.",
    severity: "Низкий — ситуация под контролем.",
    action: "Запланировать ремонт дорожного полотна на следующей неделе."
  }
};

export default function App() {
  const [activeLayer, setActiveLayer] = useState("both");
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const [time, setTime] = useState(new Date());
  const [hoveredDistrict, setHoveredDistrict] = useState(null);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const totalIncidents = DISTRICTS.reduce((s, d) => s + d.incidents.length, 0);
  const criticalIncidents = DISTRICTS.reduce((s, d) => s + d.incidents.filter(i => i.severity === "high").length, 0);
  const avgEnergy = Math.round(DISTRICTS.reduce((s, d) => s + d.energy, 0) / DISTRICTS.length);

  function handleDistrictClick(d) {
    setSelectedDistrict(d);
    setAiResult(null);
    setAiLoading(false);
  }

  async function handleAiAnalysis() {
    if (!selectedDistrict) return;
    setAiLoading(true);
    setAiResult(null);
    await new Promise(r => setTimeout(r, 1400));
    setAiResult(AI_SUMMARIES[selectedDistrict.id]);
    setAiLoading(false);
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0f1a",
      color: "#e2e8f0",
      fontFamily: "'DM Mono', 'Courier New', monospace",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Header */}
      <div style={{
        padding: "16px 28px",
        borderBottom: "1px solid #1e293b",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "rgba(15,23,42,0.95)",
        backdropFilter: "blur(8px)",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: "linear-gradient(135deg, #3b82f6, #06b6d4)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, fontWeight: "bold"
          }}>⚡</div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: "0.05em", color: "#f1f5f9" }}>
              SMART CITY · АЛМАТЫ
            </div>
            <div style={{ fontSize: 11, color: "#64748b", letterSpacing: "0.1em" }}>
              ПАНЕЛЬ УПРАВЛЕНИЯ · ЭНЕРГЕТИКА + ЖКХ
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#38bdf8", letterSpacing: "0.05em" }}>
              {time.toLocaleTimeString("ru-RU")}
            </div>
            <div style={{ fontSize: 11, color: "#475569" }}>
              {time.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
            </div>
          </div>
          <div style={{
            width: 10, height: 10, borderRadius: "50%",
            background: "#22c55e",
            boxShadow: "0 0 8px #22c55e",
            animation: "pulse 2s infinite"
          }} />
        </div>
      </div>

      {/* KPI Bar */}
      <div style={{
        display: "flex", gap: 1,
        background: "#0f172a",
        borderBottom: "1px solid #1e293b",
      }}>
        {[
          { label: "РАЙОНОВ", value: DISTRICTS.length, color: "#38bdf8", icon: "🗺" },
          { label: "ИНЦИДЕНТОВ ЖКХ", value: totalIncidents, color: "#f59e0b", icon: "⚠️" },
          { label: "КРИТИЧЕСКИХ", value: criticalIncidents, color: "#ef4444", icon: "🔴" },
          { label: "НАГРУЗКА СЕТИ", value: `${avgEnergy}%`, color: avgEnergy > 80 ? "#ef4444" : avgEnergy > 65 ? "#f59e0b" : "#22c55e", icon: "⚡" },
          { label: "СТАТУС СИСТЕМЫ", value: criticalIncidents > 1 ? "АВАРИЙНЫЙ" : "НОРМА", color: criticalIncidents > 1 ? "#ef4444" : "#22c55e", icon: criticalIncidents > 1 ? "🚨" : "✅" },
        ].map((kpi, i) => (
          <div key={i} style={{
            flex: 1, padding: "14px 20px",
            borderRight: i < 4 ? "1px solid #1e293b" : "none",
            background: "rgba(15,23,42,0.6)",
          }}>
            <div style={{ fontSize: 11, color: "#475569", letterSpacing: "0.12em", marginBottom: 4 }}>
              {kpi.icon} {kpi.label}
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: kpi.color }}>
              {kpi.value}
            </div>
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div style={{ display: "flex", flex: 1, gap: 0 }}>

        {/* Map Panel */}
        <div style={{ flex: 1, padding: "20px", position: "relative" }}>
          {/* Layer Toggles */}
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {[
              { key: "energy", label: "⚡ Энергетика" },
              { key: "incidents", label: "🔧 ЖКХ" },
              { key: "both", label: "◎ Оба слоя" },
            ].map(btn => (
              <button key={btn.key} onClick={() => setActiveLayer(btn.key)} style={{
                padding: "6px 14px", borderRadius: 6, border: "none", cursor: "pointer",
                fontSize: 12, fontFamily: "inherit", letterSpacing: "0.05em",
                background: activeLayer === btn.key ? "#3b82f6" : "#1e293b",
                color: activeLayer === btn.key ? "#fff" : "#94a3b8",
                transition: "all 0.2s",
              }}>{btn.label}</button>
            ))}
            <div style={{ flex: 1 }} />
            <div style={{ fontSize: 11, color: "#475569", alignSelf: "center" }}>
              Нажмите на район для анализа ИИ
            </div>
          </div>

          {/* Map SVG */}
          <div style={{
            background: "#0d1929",
            border: "1px solid #1e293b",
            borderRadius: 12,
            overflow: "hidden",
            position: "relative",
          }}>
            {/* Grid overlay */}
            <svg width="100%" height="380" viewBox="0 0 640 380" style={{ display: "block" }}>
              {/* Background grid */}
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.5" />
                </pattern>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              </defs>

              <rect width="640" height="380" fill="#0d1929" />
              <rect width="640" height="380" fill="url(#grid)" />

              {/* Roads (decorative) */}
              <line x1="0" y1="170" x2="640" y2="170" stroke="#1e3a5f" strokeWidth="8" />
              <line x1="290" y1="0" x2="290" y2="380" stroke="#1e3a5f" strokeWidth="6" />
              <line x1="450" y1="0" x2="450" y2="380" stroke="#1e3a5f" strokeWidth="4" />
              <line x1="0" y1="320" x2="640" y2="320" stroke="#1e3a5f" strokeWidth="4" />

              {/* Districts */}
              {DISTRICTS.map(d => {
                const isSelected = selectedDistrict?.id === d.id;
                const isHovered = hoveredDistrict === d.id;
                const hasHighIncident = d.incidents.some(i => i.severity === "high");

                return (
                  <g key={d.id}
                    onClick={() => handleDistrictClick(d)}
                    onMouseEnter={() => setHoveredDistrict(d.id)}
                    onMouseLeave={() => setHoveredDistrict(null)}
                    style={{ cursor: "pointer" }}
                  >
                    {/* Energy fill */}
                    {(activeLayer === "energy" || activeLayer === "both") && (
                      <rect
                        x={d.x} y={d.y} width={d.w} height={d.h}
                        rx={6}
                        fill={energyColor(d.energy)}
                        fillOpacity={energyOpacity(d.energy)}
                        stroke={isSelected ? "#38bdf8" : isHovered ? "#64748b" : "transparent"}
                        strokeWidth={isSelected ? 2.5 : 1.5}
                      />
                    )}

                    {/* Base border */}
                    {activeLayer === "incidents" && (
                      <rect
                        x={d.x} y={d.y} width={d.w} height={d.h}
                        rx={6}
                        fill="#1e293b"
                        fillOpacity={0.6}
                        stroke={isSelected ? "#38bdf8" : "#334155"}
                        strokeWidth={isSelected ? 2.5 : 1}
                      />
                    )}

                    {/* District name */}
                    <text
                      x={d.x + d.w / 2} y={d.y + 22}
                      textAnchor="middle"
                      fontSize="11"
                      fontFamily="DM Mono, monospace"
                      fontWeight="600"
                      fill="#e2e8f0"
                      letterSpacing="0.05em"
                    >{d.name.toUpperCase()}</text>

                    {/* Energy bar */}
                    {(activeLayer === "energy" || activeLayer === "both") && (
                      <>
                        <rect x={d.x + 10} y={d.y + 32} width={d.w - 20} height={6} rx={3} fill="#0f172a" fillOpacity={0.7} />
                        <rect x={d.x + 10} y={d.y + 32} width={(d.w - 20) * d.energy / 100} height={6} rx={3} fill={energyColor(d.energy)} />
                        <text x={d.x + d.w / 2} y={d.y + 50} textAnchor="middle" fontSize="14" fontWeight="700" fontFamily="monospace" fill={energyColor(d.energy)}>
                          {d.energy}%
                        </text>
                        <text x={d.x + d.w / 2} y={d.y + 63} textAnchor="middle" fontSize="9" fontFamily="monospace" fill="#64748b">
                          НАГРУЗКА {d.energyTrend}
                        </text>
                      </>
                    )}

                    {/* Incident dots */}
                    {(activeLayer === "incidents" || activeLayer === "both") && d.incidents.map((inc, idx) => (
                      <g key={inc.id} filter="url(#glow)">
                        <circle
                          cx={d.x + 20 + (idx % 4) * 28}
                          cy={d.y + d.h - 30 + Math.floor(idx / 4) * 22}
                          r={7}
                          fill={SEVERITY_COLOR[inc.severity]}
                          fillOpacity={0.9}
                        />
                        <text
                          x={d.x + 20 + (idx % 4) * 28}
                          y={d.y + d.h - 26 + Math.floor(idx / 4) * 22}
                          textAnchor="middle"
                          fontSize="8"
                        >{TYPE_ICON[inc.type]}</text>
                      </g>
                    ))}

                    {/* Critical badge */}
                    {hasHighIncident && (activeLayer === "incidents" || activeLayer === "both") && (
                      <g filter="url(#glow)">
                        <circle cx={d.x + d.w - 12} cy={d.y + 12} r={8} fill="#ef4444" />
                        <text x={d.x + d.w - 12} y={d.y + 16} textAnchor="middle" fontSize="10" fill="white" fontWeight="bold">!</text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* Legend */}
              <g transform="translate(10, 340)">
                {[
                  { color: "#ef4444", label: "Высокая нагрузка / Критично" },
                  { color: "#f59e0b", label: "Средняя" },
                  { color: "#22c55e", label: "Норма" },
                ].map((l, i) => (
                  <g key={i} transform={`translate(${i * 180}, 0)`}>
                    <rect width={12} height={12} rx={3} fill={l.color} fillOpacity={0.8} />
                    <text x={18} y={10} fontSize="10" fill="#94a3b8" fontFamily="monospace">{l.label}</text>
                  </g>
                ))}
              </g>
            </svg>
          </div>
        </div>

        {/* Side Panel */}
        <div style={{
          width: 340,
          borderLeft: "1px solid #1e293b",
          background: "#0a0f1a",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}>
          {!selectedDistrict ? (
            <div style={{
              flex: 1, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              padding: 32, color: "#334155", textAlign: "center",
            }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>🗺️</div>
              <div style={{ fontSize: 13, lineHeight: 1.6 }}>
                Выберите район на карте для просмотра деталей и AI-анализа
              </div>
            </div>
          ) : (
            <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
              {/* District Header */}
              <div style={{
                padding: "14px 16px",
                background: "#0f172a",
                borderRadius: 10,
                border: "1px solid #1e293b",
                marginBottom: 16,
              }}>
                <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 4 }}>ВЫБРАННЫЙ РАЙОН</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", marginBottom: 8 }}>
                  {selectedDistrict.name}
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <span style={{
                    padding: "3px 10px", borderRadius: 20,
                    background: `${energyColor(selectedDistrict.energy)}22`,
                    border: `1px solid ${energyColor(selectedDistrict.energy)}44`,
                    color: energyColor(selectedDistrict.energy),
                    fontSize: 11,
                  }}>⚡ {selectedDistrict.energy}% нагрузка</span>
                  <span style={{
                    padding: "3px 10px", borderRadius: 20,
                    background: selectedDistrict.incidents.length > 0 ? "#f59e0b22" : "#22c55e22",
                    border: `1px solid ${selectedDistrict.incidents.length > 0 ? "#f59e0b44" : "#22c55e44"}`,
                    color: selectedDistrict.incidents.length > 0 ? "#f59e0b" : "#22c55e",
                    fontSize: 11,
                  }}>🔧 {selectedDistrict.incidents.length} инцидентов</span>
                </div>
              </div>

              {/* Incidents */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, color: "#475569", letterSpacing: "0.1em", marginBottom: 10 }}>
                  ИНЦИДЕНТЫ ЖКХ
                </div>
                {selectedDistrict.incidents.length === 0 ? (
                  <div style={{
                    padding: "12px 14px", background: "#0f172a", borderRadius: 8,
                    border: "1px solid #1e293b", color: "#22c55e", fontSize: 12,
                  }}>✅ Активных инцидентов нет</div>
                ) : (
                  selectedDistrict.incidents.map(inc => (
                    <div key={inc.id} style={{
                      padding: "10px 14px",
                      background: "#0f172a",
                      borderRadius: 8,
                      border: `1px solid ${SEVERITY_COLOR[inc.severity]}33`,
                      marginBottom: 8,
                      borderLeft: `3px solid ${SEVERITY_COLOR[inc.severity]}`,
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 12, color: "#e2e8f0" }}>
                          {TYPE_ICON[inc.type]} {inc.desc}
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: 8 }}>
                        <span style={{
                          fontSize: 10, padding: "2px 8px", borderRadius: 12,
                          background: `${SEVERITY_COLOR[inc.severity]}22`,
                          color: SEVERITY_COLOR[inc.severity],
                        }}>{SEVERITY_LABEL[inc.severity]}</span>
                        <span style={{ fontSize: 10, color: "#475569" }}>🕐 {inc.time}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* AI Analysis Button */}
              <button onClick={handleAiAnalysis} disabled={aiLoading} style={{
                width: "100%",
                padding: "12px",
                borderRadius: 8,
                border: "none",
                cursor: aiLoading ? "wait" : "pointer",
                background: aiLoading
                  ? "#1e293b"
                  : "linear-gradient(135deg, #3b82f6, #06b6d4)",
                color: aiLoading ? "#475569" : "#fff",
                fontSize: 13,
                fontFamily: "inherit",
                fontWeight: 600,
                letterSpacing: "0.05em",
                marginBottom: 16,
                transition: "all 0.2s",
              }}>
                {aiLoading ? "⏳ Анализирую данные..." : "🤖 AI-АНАЛИЗ РАЙОНА"}
              </button>

              {/* AI Result */}
              {aiResult && (
                <div style={{
                  background: "#0f172a",
                  border: `1px solid ${aiResult.color}44`,
                  borderRadius: 10,
                  overflow: "hidden",
                }}>
                  <div style={{
                    padding: "10px 14px",
                    background: `${aiResult.color}22`,
                    borderBottom: `1px solid ${aiResult.color}33`,
                    display: "flex", alignItems: "center", gap: 8,
                  }}>
                    <span style={{ fontSize: 12, color: aiResult.color, fontWeight: 700 }}>
                      🤖 AI · СТАТУС: {aiResult.status.toUpperCase()}
                    </span>
                  </div>
                  {[
                    { icon: "📊", label: "ЧТО ПРОИСХОДИТ", text: aiResult.what },
                    { icon: "⚠️", label: "КРИТИЧНОСТЬ", text: aiResult.severity },
                    { icon: "✅", label: "ДЕЙСТВИЯ", text: aiResult.action },
                  ].map((s, i) => (
                    <div key={i} style={{
                      padding: "12px 14px",
                      borderBottom: i < 2 ? "1px solid #1e293b" : "none",
                    }}>
                      <div style={{ fontSize: 10, color: "#475569", letterSpacing: "0.1em", marginBottom: 4 }}>
                        {s.icon} {s.label}
                      </div>
                      <div style={{ fontSize: 12, color: "#cbd5e1", lineHeight: 1.6 }}>
                        {s.text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Bottom status */}
          <div style={{
            padding: "12px 20px",
            borderTop: "1px solid #1e293b",
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <span style={{ fontSize: 10, color: "#334155" }}>ДАННЫЕ ОБНОВЛЕНЫ: {time.toLocaleTimeString("ru-RU")}</span>
            <span style={{
              fontSize: 10, padding: "2px 8px", borderRadius: 10,
              background: "#22c55e22", color: "#22c55e",
            }}>● LIVE</span>
          </div>
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap');
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0a0f1a; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
      `}</style>
    </div>
  );
}
