import React, { useState, useEffect } from 'react';
import api from '../api';
import { Navbar } from '../components/Navbar';

export const Sessions = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // New session form
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [durationMin, setDurationMin] = useState(45);
  const [notes, setNotes] = useState('');

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const res = await api.get('/sessions');
      setSessions(res.data);
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError('Failed to fetch workout sessions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleCreateSession = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);

    try {
      const payload = {
        date,
        duration_min: Number(durationMin),
        notes: notes.trim() || undefined,
      };

      const res = await api.post('/sessions', payload);
      setSessions([res.data, ...sessions]);
      setNotes('');
      setSuccess('Workout session logged successfully!');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Failed to log session.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSession = async (id) => {
    if (!window.confirm('Are you sure you want to delete this session?')) return;
    try {
      await api.delete(`/sessions/${id}`);
      setSessions(sessions.filter((s) => s.id !== id));
      setSuccess('Session deleted.');
    } catch (err) {
      setError('Failed to delete session.');
    }
  };

  const handleStravaSync = async () => {
    setError('');
    setSuccess('');
    setSyncing(true);
    try {
      const res = await api.post('/integrations/strava/sync');
      setSuccess(`Strava sync completed! Synced ${res.data?.synced_count || 0} activities.`);
      fetchSessions();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Strava sync failed. Ensure your Strava account is connected.');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div style={styles.page}>
      <Navbar />
      <div style={styles.container}>
        <div style={styles.header}>
          <div>
            <h1 style={styles.pageTitle}>Workout Sessions</h1>
            <p style={styles.subTitle}>Track completed workouts and sync with Strava</p>
          </div>
          <button onClick={handleStravaSync} disabled={syncing} style={styles.syncBtn}>
            {syncing ? 'Syncing...' : '🔄 Sync with Strava'}
          </button>
        </div>

        {error && <div style={styles.errorAlert}>{error}</div>}
        {success && <div style={styles.successAlert}>{success}</div>}

        <div style={styles.layout}>
          {/* New Session Form */}
          <div style={styles.card}>
            <h2 style={styles.sectionTitle}>Log Workout Session</h2>
            <form onSubmit={handleCreateSession} style={styles.form}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Date</label>
                <input
                  type="date"
                  required
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  style={styles.input}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Duration (minutes)</label>
                <input
                  type="number"
                  required
                  min="1"
                  max="720"
                  value={durationMin}
                  onChange={(e) => setDurationMin(e.target.value)}
                  style={styles.input}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Notes / Summary</label>
                <textarea
                  rows="3"
                  placeholder="e.g. Upper body push workout, benched 85kg 3x8, felt strong"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  style={styles.textarea}
                ></textarea>
              </div>

              <button type="submit" disabled={submitting} style={styles.submitBtn}>
                {submitting ? 'Saving...' : '💾 Save Session'}
              </button>
            </form>
          </div>

          {/* Sessions List */}
          <div style={styles.listSection}>
            <h2 style={styles.sectionTitle}>Session History ({sessions.length})</h2>
            {loading ? (
              <p style={styles.emptyText}>Loading sessions...</p>
            ) : sessions.length === 0 ? (
              <div style={styles.emptyBox}>
                <p>No workout sessions logged yet.</p>
                <p style={styles.emptySub}>Log a session manually or connect Strava to sync automatically.</p>
              </div>
            ) : (
              <div style={styles.sessionList}>
                {sessions.map((sess) => (
                  <div key={sess.id} style={styles.sessionCard}>
                    <div style={styles.sessionHeader}>
                      <div>
                        <span style={styles.sessionDate}>
                          📅 {new Date(sess.date).toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
                        </span>
                        <span style={styles.sessionDuration}> • ⏱️ {sess.duration_min} mins</span>
                      </div>
                      <div style={styles.headerRight}>
                        {sess.strava_activity_id ? (
                          <span style={styles.stravaBadge}>Strava Activity</span>
                        ) : (
                          <span style={styles.manualBadge}>Manual Entry</span>
                        )}
                        <button
                          onClick={() => handleDeleteSession(sess.id)}
                          style={styles.deleteBtn}
                          title="Delete session"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                    {sess.notes && <p style={styles.sessionNotes}>{sess.notes}</p>}
                  </div>
                ))}
              </div>
            )}
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
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '24px 20px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  pageTitle: {
    fontSize: '28px',
    fontWeight: '800',
    color: '#0f172a',
    margin: 0,
  },
  subTitle: {
    fontSize: '15px',
    color: '#64748b',
    margin: '4px 0 0 0',
  },
  syncBtn: {
    padding: '10px 18px',
    backgroundColor: '#fc5200',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    fontWeight: '700',
    fontSize: '14px',
    cursor: 'pointer',
  },
  errorAlert: {
    backgroundColor: '#fee2e2',
    color: '#991b1b',
    padding: '12px 16px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  successAlert: {
    backgroundColor: '#dcfce7',
    color: '#166534',
    padding: '12px 16px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '360px 1fr',
    gap: '24px',
    alignItems: 'start',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#1e293b',
    margin: '0 0 16px 0',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#475569',
  },
  input: {
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    fontSize: '14px',
    outline: 'none',
  },
  textarea: {
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    fontSize: '14px',
    outline: 'none',
    fontFamily: 'inherit',
    resize: 'vertical',
  },
  submitBtn: {
    padding: '12px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '15px',
    fontWeight: '700',
    cursor: 'pointer',
    marginTop: '6px',
  },
  listSection: {
    display: 'flex',
    flexDirection: 'column',
  },
  sessionList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  sessionCard: {
    backgroundColor: '#ffffff',
    borderRadius: '10px',
    padding: '16px 20px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
    border: '1px solid #e2e8f0',
  },
  sessionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  sessionDate: {
    fontWeight: '700',
    color: '#0f172a',
    fontSize: '15px',
  },
  sessionDuration: {
    color: '#64748b',
    fontSize: '14px',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  stravaBadge: {
    backgroundColor: '#ffedd5',
    color: '#c2410c',
    padding: '3px 8px',
    borderRadius: '999px',
    fontSize: '11px',
    fontWeight: '700',
  },
  manualBadge: {
    backgroundColor: '#f1f5f9',
    color: '#475569',
    padding: '3px 8px',
    borderRadius: '999px',
    fontSize: '11px',
    fontWeight: '600',
  },
  deleteBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '4px',
  },
  sessionNotes: {
    margin: '8px 0 0 0',
    fontSize: '14px',
    color: '#334155',
    lineHeight: '1.4',
  },
  emptyBox: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    padding: '48px 20px',
    textAlign: 'center',
    color: '#64748b',
  },
  emptySub: {
    fontSize: '13px',
    color: '#94a3b8',
    marginTop: '6px',
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: '14px',
  },
};
