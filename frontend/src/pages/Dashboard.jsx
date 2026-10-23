import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import api from '../api';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export const Dashboard = () => {
  const { user } = useAuth();

  // Coaching state
  const [briefing, setBriefing] = useState(null);
  const [review, setReview] = useState(null);

  // Strava state
  const [stravaStatus, setStravaStatus] = useState(null);
  const [syncingStrava, setSyncingStrava] = useState(false);
  const [stravaMsg, setStravaMsg] = useState('');

  // Analytics data
  const [sessionMinutesData, setSessionMinutesData] = useState([]);
  const [adherenceData, setAdherenceData] = useState([]);
  const [caloriesData, setCaloriesData] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      // Fetch briefing & review (ignoring 404s if none generated yet)
      try {
        const bRes = await api.get('/briefings/today');
        setBriefing(bRes.data);
      } catch (e) {
        setBriefing(null);
      }

      try {
        const rRes = await api.get('/reviews/latest');
        setReview(rRes.data);
      } catch (e) {
        setReview(null);
      }

      // Fetch Strava status
      try {
        const sRes = await api.get('/integrations/strava/status');
        setStravaStatus(sRes.data);
      } catch (e) {
        setStravaStatus(null);
      }

      // Fetch sessions for charts
      const sessionsRes = await api.get('/sessions');
      const sessions = sessionsRes.data || [];

      // Compute last 7 days session minutes
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const today = new Date();
      const last7Days = [];
      for (let i = 6; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const dateStr = d.toISOString().split('T')[0];
        const dayLabel = days[d.getDay()];

        // Find sessions on this date
        const daySessions = sessions.filter((s) => s.date === dateStr);
        const totalMin = daySessions.reduce((acc, curr) => acc + (curr.duration_min || 0), 0);

        last7Days.push({
          date: dateStr,
          day: dayLabel,
          minutes: totalMin,
          sessionsCount: daySessions.length,
        });
      }
      setSessionMinutesData(last7Days);

      // Adherence: Planned vs Done (based on sessions and target ~4 sessions/week)
      const totalSessionsDone = sessions.length;
      const plannedWeekly = 4;
      setAdherenceData([
        { name: 'This Week', done: Math.min(totalSessionsDone, plannedWeekly), planned: plannedWeekly },
      ]);

      // Daily nutrition calories for past 5 days
      const calHistory = [];
      for (let i = 4; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const dateStr = d.toISOString().split('T')[0];
        try {
          const sumRes = await api.get(`/nutrition/summary?date=${dateStr}`);
          calHistory.push({
            date: dateStr.slice(5),
            calories: sumRes.data.total_calories || 0,
            target: 2200,
          });
        } catch {
          calHistory.push({
            date: dateStr.slice(5),
            calories: 0,
            target: 2200,
          });
        }
      }
      setCaloriesData(calHistory);

    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleConnectStrava = async () => {
    try {
      const res = await api.get('/integrations/strava/connect?redirect=false');
      if (res.data?.authorization_url) {
        window.location.href = res.data.authorization_url;
      }
    } catch (err) {
      setStravaMsg('Failed to initiate Strava OAuth.');
    }
  };

  const handleSyncStrava = async () => {
    setSyncingStrava(true);
    setStravaMsg('');
    try {
      const res = await api.post('/integrations/strava/sync');
      setStravaMsg(`Successfully synced ${res.data?.synced_count || 0} activities!`);
      fetchDashboardData();
    } catch (err) {
      setStravaMsg('Failed to sync Strava activities.');
    } finally {
      setSyncingStrava(false);
    }
  };

  const handleDisconnectStrava = async () => {
    if (!window.confirm('Disconnect Strava account?')) return;
    try {
      await api.post('/integrations/strava/disconnect');
      setStravaMsg('Strava account disconnected.');
      fetchDashboardData();
    } catch (err) {
      setStravaMsg('Failed to disconnect Strava.');
    }
  };

  return (
    <div style={styles.page}>
      <Navbar />
      <div style={styles.container}>
        {/* Welcome Header */}
        <div style={styles.headerCard}>
          <div>
            <h1 style={styles.heading}>Welcome back, {user?.email || 'Athlete'}! 👋</h1>
            <p style={styles.subHeading}>
              Here is your training progress, coaching briefing, and daily performance overview.
            </p>
          </div>
          {/* Strava Integration Card */}
          <div style={styles.stravaBox}>
            <div style={styles.stravaHeader}>
              <span style={styles.stravaTitle}>🟠 Strava Sync</span>
              <span style={stravaStatus?.is_connected ? styles.connectedTag : styles.disconnectedTag}>
                {stravaStatus?.is_connected ? 'Connected' : 'Not Connected'}
              </span>
            </div>
            {stravaMsg && <div style={styles.stravaMsg}>{stravaMsg}</div>}
            <div style={styles.stravaActions}>
              {stravaStatus?.is_connected ? (
                <>
                  <button onClick={handleSyncStrava} disabled={syncingStrava} style={styles.syncBtn}>
                    {syncingStrava ? 'Syncing...' : '🔄 Sync Activities'}
                  </button>
                  <button onClick={handleDisconnectStrava} style={styles.disconnectBtn}>
                    Disconnect
                  </button>
                </>
              ) : (
                <button onClick={handleConnectStrava} style={styles.connectBtn}>
                  Connect Strava Account
                </button>
              )}
            </div>
          </div>
        </div>

        {/* AI Coaching Row */}
        <div style={styles.coachingGrid}>
          {/* Daily Briefing */}
          <div style={styles.coachingCard}>
            <div style={styles.coachingHeader}>
              <h3 style={styles.cardHeading}>🌅 Today's Workout Briefing</h3>
              <span style={styles.badge}>Daily</span>
            </div>
            {briefing ? (
              <div style={styles.coachingBody}>
                <p style={styles.briefingText}>{briefing.summary}</p>
                <span style={styles.dateSmall}>{briefing.date}</span>
              </div>
            ) : (
              <p style={styles.emptyText}>
                No briefing generated for today yet. Scheduled jobs run each morning at 07:00 UTC.
              </p>
            )}
          </div>

          {/* Weekly Review */}
          <div style={styles.coachingCard}>
            <div style={styles.coachingHeader}>
              <h3 style={styles.cardHeading}>📊 Weekly Performance Review</h3>
              <span style={styles.badge}>Weekly</span>
            </div>
            {review ? (
              <div style={styles.coachingBody}>
                <p style={styles.briefingText}>{review.summary}</p>
                {review.next_week_suggestions && (
                  <div style={styles.suggestionsBox}>
                    <strong>Next Week Focus:</strong> {review.next_week_suggestions}
                  </div>
                )}
                <div style={styles.statsRow}>
                  <span>⏱️ {review.total_minutes} mins</span> •{' '}
                  <span>🏋️ {review.total_sessions} sessions</span> •{' '}
                  <span>📈 {review.total_volume} kg volume</span>
                </div>
              </div>
            ) : (
              <p style={styles.emptyText}>
                No weekly review available yet. Scheduled jobs generate comprehensive reviews every Sunday.
              </p>
            )}
          </div>
        </div>

        {/* Charts & Analytics Grid */}
        <div style={styles.chartsGrid}>
          {/* Chart 1: Training Session Minutes */}
          <div style={styles.chartCard}>
            <h3 style={styles.cardHeading}>Training Minutes (Last 7 Days)</h3>
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={sessionMinutesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="day" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Bar dataKey="minutes" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Minutes" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Daily Calories Trend */}
          <div style={styles.chartCard}>
            <h3 style={styles.cardHeading}>Daily Calorie Intake (vs 2,200 kcal target)</h3>
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={caloriesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="calories" stroke="#10b981" strokeWidth={3} name="Intake (kcal)" />
                  <Line type="monotone" dataKey="target" stroke="#cbd5e1" strokeDasharray="5 5" name="Target" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  page: {
    minHeight: '100vh',
    backgroundColor: '#f8fafc',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '24px 20px',
  },
  headerCard: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    padding: '24px 28px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '20px',
    marginBottom: '24px',
  },
  heading: {
    margin: '0 0 6px 0',
    fontSize: '26px',
    fontWeight: '800',
    color: '#0f172a',
  },
  subHeading: {
    margin: 0,
    fontSize: '15px',
    color: '#64748b',
  },
  stravaBox: {
    backgroundColor: '#fff7ed',
    border: '1px solid #ffedd5',
    borderRadius: '10px',
    padding: '14px 18px',
    minWidth: '280px',
  },
  stravaHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  stravaTitle: {
    fontWeight: '700',
    fontSize: '14px',
    color: '#9a3412',
  },
  connectedTag: {
    backgroundColor: '#dcfce7',
    color: '#166534',
    fontSize: '11px',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '999px',
  },
  disconnectedTag: {
    backgroundColor: '#f1f5f9',
    color: '#64748b',
    fontSize: '11px',
    fontWeight: '600',
    padding: '2px 8px',
    borderRadius: '999px',
  },
  stravaMsg: {
    fontSize: '12px',
    color: '#c2410c',
    marginBottom: '8px',
  },
  stravaActions: {
    display: 'flex',
    gap: '8px',
  },
  connectBtn: {
    backgroundColor: '#fc5200',
    color: '#ffffff',
    border: 'none',
    padding: '8px 14px',
    borderRadius: '6px',
    fontWeight: '700',
    fontSize: '13px',
    cursor: 'pointer',
    width: '100%',
  },
  syncBtn: {
    backgroundColor: '#fc5200',
    color: '#ffffff',
    border: 'none',
    padding: '6px 12px',
    borderRadius: '6px',
    fontWeight: '600',
    fontSize: '13px',
    cursor: 'pointer',
  },
  disconnectBtn: {
    backgroundColor: 'transparent',
    border: '1px solid #fed7aa',
    color: '#9a3412',
    padding: '6px 10px',
    borderRadius: '6px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  coachingGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
    gap: '20px',
    marginBottom: '24px',
  },
  coachingCard: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    padding: '20px 24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
  },
  coachingHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  cardHeading: {
    margin: 0,
    fontSize: '17px',
    fontWeight: '700',
    color: '#1e293b',
  },
  badge: {
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    fontSize: '11px',
    fontWeight: '700',
    padding: '3px 8px',
    borderRadius: '999px',
  },
  coachingBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  briefingText: {
    margin: 0,
    fontSize: '14px',
    color: '#334155',
    lineHeight: '1.5',
  },
  suggestionsBox: {
    backgroundColor: '#f8fafc',
    borderLeft: '3px solid #3b82f6',
    padding: '8px 12px',
    fontSize: '13px',
    color: '#475569',
    borderRadius: '0 6px 6px 0',
  },
  statsRow: {
    fontSize: '12px',
    color: '#64748b',
    marginTop: '4px',
  },
  dateSmall: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  chartsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))',
    gap: '20px',
  },
  chartCard: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    padding: '20px 24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: '14px',
    margin: 0,
  },
};
