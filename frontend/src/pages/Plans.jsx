import React, { useState, useEffect } from 'react';
import api from '../api';
import { Navbar } from '../components/Navbar';

export const Plans = () => {
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState('');
  const [error, setError] = useState('');

  // Form state
  const [goal, setGoal] = useState('Strength');
  const [level, setLevel] = useState('Intermediate');
  const [equipment, setEquipment] = useState('Full Gym');
  const [daysPerWeek, setDaysPerWeek] = useState(3);
  const [weeks, setWeeks] = useState(4);
  const [injuries, setInjuries] = useState('');

  const fetchPlans = async () => {
    try {
      setLoadingList(true);
      const res = await api.get('/plans');
      setPlans(res.data);
      if (res.data.length > 0 && !selectedPlan) {
        setSelectedPlan(res.data[0]);
      }
    } catch (err) {
      console.error('Failed to load plans:', err);
      setError('Unable to load workout plans.');
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError('');
    setGenerating(true);
    setGenerationStatus('Submitting generation request...');

    try {
      const payload = {
        goal,
        level,
        equipment,
        days_per_week: Number(daysPerWeek),
        weeks: Number(weeks),
        injuries: injuries.trim() || undefined,
      };

      const response = await api.post('/plans/generate-async', payload);
      const { task_id } = response.data;
      setGenerationStatus('AI Coach is designing your personalized plan...');

      // Poll task status
      const pollInterval = setInterval(async () => {
        try {
          const taskRes = await api.get(`/tasks/${task_id}`);
          const { status, plan_id, error: taskError } = taskRes.data;

          if (status === 'success' && plan_id) {
            clearInterval(pollInterval);
            setGenerationStatus('Plan generated successfully!');
            const planRes = await api.get(`/plans/${plan_id}`);
            setPlans((prev) => [planRes.data, ...prev]);
            setSelectedPlan(planRes.data);
            setGenerating(false);
          } else if (status === 'failure') {
            clearInterval(pollInterval);
            setError(taskError || 'Plan generation failed. Please try again.');
            setGenerating(false);
          } else {
            setGenerationStatus(`Processing... (Status: ${status})`);
          }
        } catch (pollErr) {
          clearInterval(pollInterval);
          setError('Lost connection while polling task status.');
          setGenerating(false);
        }
      }, 2000);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Failed to start plan generation.');
      setGenerating(false);
    }
  };

  return (
    <div style={styles.page}>
      <Navbar />
      <div style={styles.container}>
        <h1 style={styles.pageTitle}>AI Workout Plans</h1>

        {error && <div style={styles.errorAlert}>{error}</div>}

        <div style={styles.layout}>
          {/* Generation Form Sidebar */}
          <div style={styles.sidebar}>
            <div style={styles.card}>
              <h2 style={styles.sectionTitle}>Generate New Plan</h2>
              <form onSubmit={handleGenerate} style={styles.form}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Primary Goal</label>
                  <select value={goal} onChange={(e) => setGoal(e.target.value)} style={styles.select}>
                    <option value="Strength">Strength & Power</option>
                    <option value="Hypertrophy">Muscle Hypertrophy</option>
                    <option value="Endurance">Cardio & Endurance</option>
                    <option value="Fat Loss">Fat Loss & Conditioning</option>
                    <option value="General Fitness">General Fitness</option>
                  </select>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>Experience Level</label>
                  <select value={level} onChange={(e) => setLevel(e.target.value)} style={styles.select}>
                    <option value="Beginner">Beginner</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Advanced">Advanced</option>
                  </select>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>Equipment</label>
                  <select value={equipment} onChange={(e) => setEquipment(e.target.value)} style={styles.select}>
                    <option value="Full Gym">Full Gym</option>
                    <option value="Dumbbells Only">Dumbbells Only</option>
                    <option value="Barbell & Rack">Barbell & Rack</option>
                    <option value="Bodyweight">Bodyweight Only</option>
                  </select>
                </div>

                <div style={styles.row}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Days / Week</label>
                    <input
                      type="number"
                      min="1"
                      max="7"
                      value={daysPerWeek}
                      onChange={(e) => setDaysPerWeek(e.target.value)}
                      style={styles.input}
                    />
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>Weeks</label>
                    <input
                      type="number"
                      min="1"
                      max="12"
                      value={weeks}
                      onChange={(e) => setWeeks(e.target.value)}
                      style={styles.input}
                    />
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>Injuries or Limitations</label>
                  <input
                    type="text"
                    placeholder="e.g. Lower back pain, no squats"
                    value={injuries}
                    onChange={(e) => setInjuries(e.target.value)}
                    style={styles.input}
                  />
                </div>

                <button type="submit" disabled={generating} style={styles.generateBtn}>
                  {generating ? 'Generating...' : '⚡ Generate Plan'}
                </button>

                {generating && (
                  <div style={styles.statusBox}>
                    <div style={styles.spinner}></div>
                    <span style={styles.statusText}>{generationStatus}</span>
                  </div>
                )}
              </form>
            </div>

            {/* Past Plans List */}
            <div style={{ ...styles.card, marginTop: '20px' }}>
              <h3 style={styles.sectionTitle}>Saved Plans ({plans.length})</h3>
              {loadingList ? (
                <p style={styles.emptyText}>Loading plans...</p>
              ) : plans.length === 0 ? (
                <p style={styles.emptyText}>No plans generated yet.</p>
              ) : (
                <div style={styles.planList}>
                  {plans.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => setSelectedPlan(p)}
                      style={{
                        ...styles.planListItem,
                        backgroundColor: selectedPlan?.id === p.id ? '#eff6ff' : '#ffffff',
                        borderColor: selectedPlan?.id === p.id ? '#3b82f6' : '#e5e7eb',
                      }}
                    >
                      <strong style={styles.planItemTitle}>
                        {p.inputs?.goal || 'Custom Plan'} ({p.inputs?.weeks || 4} Weeks)
                      </strong>
                      <span style={styles.planItemDate}>
                        Created: {new Date(p.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Plan Viewer Main Area */}
          <div style={styles.mainContent}>
            {selectedPlan ? (
              <div style={styles.card}>
                <div style={styles.planHeader}>
                  <div>
                    <h2 style={styles.planName}>
                      {selectedPlan.inputs?.goal} Program ({selectedPlan.inputs?.level})
                    </h2>
                    <p style={styles.planMeta}>
                      Equipment: {selectedPlan.inputs?.equipment} • {selectedPlan.inputs?.days_per_week} Days/Week • {selectedPlan.inputs?.weeks} Weeks
                    </p>
                  </div>
                  <span style={styles.providerBadge}>Provider: {selectedPlan.provider || 'AI'}</span>
                </div>

                <div style={styles.weeksContainer}>
                  {selectedPlan.plan?.weeks?.map((week) => (
                    <div key={week.number} style={styles.weekCard}>
                      <h3 style={styles.weekHeading}>Week {week.number}</h3>
                      <div style={styles.daysGrid}>
                        {week.days?.map((day, idx) => (
                          <div key={idx} style={styles.dayCard}>
                            <div style={styles.dayHeader}>
                              <h4 style={styles.dayName}>{day.name}</h4>
                              <span style={styles.dayFocus}>{day.focus}</span>
                            </div>
                            <table style={styles.exerciseTable}>
                              <thead>
                                <tr>
                                  <th style={styles.th}>Exercise</th>
                                  <th style={styles.th}>Sets</th>
                                  <th style={styles.th}>Reps</th>
                                  <th style={styles.th}>Rest</th>
                                </tr>
                              </thead>
                              <tbody>
                                {day.exercises?.map((ex, exIdx) => (
                                  <tr key={exIdx} style={styles.tr}>
                                    <td style={styles.td}>
                                      <strong>{ex.name}</strong>
                                      {ex.notes && <div style={styles.exNotes}>{ex.notes}</div>}
                                    </td>
                                    <td style={styles.tdCenter}>{ex.sets}</td>
                                    <td style={styles.tdCenter}>{ex.reps}</td>
                                    <td style={styles.tdCenter}>{ex.rest_sec || 60}s</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={styles.card}>
                <div style={styles.placeholderBox}>
                  <h3>Select or generate a plan</h3>
                  <p>Choose an existing plan from the list or fill out the form to create a new one.</p>
                </div>
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
    maxWidth: '1280px',
    margin: '0 auto',
    padding: '24px 20px',
  },
  pageTitle: {
    fontSize: '28px',
    fontWeight: '800',
    color: '#0f172a',
    marginBottom: '20px',
  },
  errorAlert: {
    backgroundColor: '#fee2e2',
    color: '#991b1b',
    padding: '12px 16px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '380px 1fr',
    gap: '24px',
    alignItems: 'start',
  },
  sidebar: {
    display: 'flex',
    flexDirection: 'column',
  },
  mainContent: {
    minWidth: 0,
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
  row: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
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
  select: {
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    fontSize: '14px',
    backgroundColor: '#ffffff',
  },
  generateBtn: {
    marginTop: '6px',
    padding: '12px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '15px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  statusBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    backgroundColor: '#eff6ff',
    padding: '10px 14px',
    borderRadius: '6px',
    marginTop: '6px',
  },
  spinner: {
    width: '16px',
    height: '16px',
    border: '2px solid #bfdbfe',
    borderTop: '2px solid #2563eb',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  statusText: {
    fontSize: '13px',
    color: '#1d4ed8',
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: '14px',
  },
  planList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    maxHeight: '320px',
    overflowY: 'auto',
  },
  planListItem: {
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  planItemTitle: {
    fontSize: '14px',
    color: '#1e293b',
  },
  planItemDate: {
    fontSize: '12px',
    color: '#64748b',
  },
  planHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottom: '1px solid #f1f5f9',
    paddingBottom: '16px',
    marginBottom: '20px',
  },
  planName: {
    fontSize: '22px',
    fontWeight: '800',
    color: '#0f172a',
    margin: '0 0 6px 0',
  },
  planMeta: {
    margin: 0,
    fontSize: '14px',
    color: '#64748b',
  },
  providerBadge: {
    backgroundColor: '#f1f5f9',
    color: '#475569',
    padding: '4px 10px',
    borderRadius: '999px',
    fontSize: '12px',
    fontWeight: '600',
  },
  weeksContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  weekCard: {
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    padding: '16px',
    backgroundColor: '#fafafa',
  },
  weekHeading: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#1e293b',
    margin: '0 0 14px 0',
  },
  daysGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '16px',
  },
  dayCard: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
    padding: '14px',
  },
  dayHeader: {
    marginBottom: '10px',
  },
  dayName: {
    margin: '0 0 2px 0',
    fontSize: '15px',
    fontWeight: '700',
    color: '#0f172a',
  },
  dayFocus: {
    fontSize: '12px',
    color: '#2563eb',
    fontWeight: '600',
  },
  exerciseTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    textAlign: 'left',
    padding: '6px 4px',
    borderBottom: '1px solid #e2e8f0',
    color: '#64748b',
    fontSize: '12px',
  },
  tr: {
    borderBottom: '1px solid #f1f5f9',
  },
  td: {
    padding: '8px 4px',
    color: '#1e293b',
  },
  tdCenter: {
    padding: '8px 4px',
    textAlign: 'center',
    color: '#475569',
  },
  exNotes: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '2px',
  },
  placeholderBox: {
    textAlign: 'center',
    padding: '60px 20px',
    color: '#64748b',
  },
};
