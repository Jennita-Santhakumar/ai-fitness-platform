import React, { useState, useEffect } from 'react';
import api from '../api';
import { Navbar } from '../components/Navbar';

export const Nutrition = () => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [logs, setLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loadingLogs, setLoadingLogs] = useState(true);

  // Search state
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [servingGrams, setServingGrams] = useState({});

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchDayData = async (dateStr) => {
    try {
      setLoadingLogs(true);
      const [logsRes, summaryRes] = await Promise.all([
        api.get(`/nutrition/logs?date=${dateStr}`),
        api.get(`/nutrition/summary?date=${dateStr}`),
      ]);
      setLogs(logsRes.data);
      setSummary(summaryRes.data);
    } catch (err) {
      console.error('Failed to fetch nutrition data:', err);
      setError('Unable to load food logs.');
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    fetchDayData(selectedDate);
  }, [selectedDate]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setError('');
    setSearching(true);
    try {
      const res = await api.get(`/nutrition/search?q=${encodeURIComponent(query.trim())}`);
      setSearchResults(res.data.results || []);
      // Initialize default serving grams (100g each)
      const initialGrams = {};
      (res.data.results || []).forEach((item) => {
        initialGrams[item.fdc_id] = item.serving_size || 100;
      });
      setServingGrams(initialGrams);
    } catch (err) {
      setError('Food search failed. Please try a different keyword.');
    } finally {
      setSearching(false);
    }
  };

  const handleAddToLog = async (food) => {
    setError('');
    setSuccess('');
    const grams = Number(servingGrams[food.fdc_id]) || 100;
    const ratio = grams / (food.serving_size || 100);

    const payload = {
      name: food.name,
      grams: grams,
      calories: Math.round(food.calories * ratio * 10) / 10,
      protein: Math.round(food.protein * ratio * 10) / 10,
      carbs: Math.round(food.carbs * ratio * 10) / 10,
      fat: Math.round(food.fat * ratio * 10) / 10,
      date: selectedDate,
      fdc_id: food.fdc_id,
    };

    try {
      await api.post('/nutrition/logs', payload);
      setSuccess(`Added ${food.name} (${grams}g) to log.`);
      fetchDayData(selectedDate);
    } catch (err) {
      setError('Failed to log food item.');
    }
  };

  const handleDeleteLog = async (id) => {
    try {
      await api.delete(`/nutrition/logs/${id}`);
      setSuccess('Item removed from log.');
      fetchDayData(selectedDate);
    } catch (err) {
      setError('Failed to remove food item.');
    }
  };

  return (
    <div style={styles.page}>
      <Navbar />
      <div style={styles.container}>
        <div style={styles.header}>
          <div>
            <h1 style={styles.pageTitle}>Nutrition & Macro Tracking</h1>
            <p style={styles.subTitle}>Search USDA foods, calculate macros, and log daily intake</p>
          </div>
          <div style={styles.dateSelector}>
            <label style={styles.dateLabel}>Date:</label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={styles.dateInput}
            />
          </div>
        </div>

        {error && <div style={styles.errorAlert}>{error}</div>}
        {success && <div style={styles.successAlert}>{success}</div>}

        {/* Daily Summary Cards */}
        <div style={styles.summaryGrid}>
          <div style={{ ...styles.summaryCard, borderLeft: '4px solid #3b82f6' }}>
            <span style={styles.summaryLabel}>Total Calories</span>
            <span style={styles.summaryValue}>{summary?.total_calories || 0} <small style={styles.unit}>kcal</small></span>
          </div>
          <div style={{ ...styles.summaryCard, borderLeft: '4px solid #10b981' }}>
            <span style={styles.summaryLabel}>Protein</span>
            <span style={styles.summaryValue}>{summary?.total_protein || 0} <small style={styles.unit}>g</small></span>
          </div>
          <div style={{ ...styles.summaryCard, borderLeft: '4px solid #f59e0b' }}>
            <span style={styles.summaryLabel}>Carbohydrates</span>
            <span style={styles.summaryValue}>{summary?.total_carbs || 0} <small style={styles.unit}>g</small></span>
          </div>
          <div style={{ ...styles.summaryCard, borderLeft: '4px solid #ef4444' }}>
            <span style={styles.summaryLabel}>Fat</span>
            <span style={styles.summaryValue}>{summary?.total_fat || 0} <small style={styles.unit}>g</small></span>
          </div>
        </div>

        <div style={styles.layout}>
          {/* Food Search Section */}
          <div style={styles.card}>
            <h2 style={styles.sectionTitle}>🔍 Search USDA Food Database</h2>
            <form onSubmit={handleSearch} style={styles.searchForm}>
              <input
                type="text"
                placeholder="e.g. Banana, Chicken Breast, Eggs, Rice"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={styles.searchInput}
              />
              <button type="submit" disabled={searching} style={styles.searchBtn}>
                {searching ? 'Searching...' : 'Search'}
              </button>
            </form>

            {searchResults.length > 0 && (
              <div style={styles.resultsList}>
                <h3 style={styles.resultsHeading}>Search Results ({searchResults.length})</h3>
                {searchResults.map((food) => (
                  <div key={food.fdc_id} style={styles.foodItem}>
                    <div style={styles.foodInfo}>
                      <strong style={styles.foodName}>{food.name}</strong>
                      <div style={styles.foodMacros}>
                        <span>🔥 {food.calories} kcal</span> •{' '}
                        <span>🥩 {food.protein}g P</span> •{' '}
                        <span>🍚 {food.carbs}g C</span> •{' '}
                        <span>🥑 {food.fat}g F</span>
                        <span style={styles.perServing}> (per {food.serving_size || 100}{food.serving_unit || 'g'})</span>
                      </div>
                    </div>
                    <div style={styles.addActions}>
                      <input
                        type="number"
                        min="1"
                        max="2000"
                        value={servingGrams[food.fdc_id] || 100}
                        onChange={(e) =>
                          setServingGrams({
                            ...servingGrams,
                            [food.fdc_id]: e.target.value,
                          })
                        }
                        style={styles.gramsInput}
                      />
                      <span style={styles.gramsUnit}>g</span>
                      <button
                        onClick={() => handleAddToLog(food)}
                        style={styles.addBtn}
                      >
                        + Add
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Today's Food Log */}
          <div style={styles.card}>
            <h2 style={styles.sectionTitle}>Daily Log ({logs.length} items)</h2>
            {loadingLogs ? (
              <p style={styles.emptyText}>Loading log...</p>
            ) : logs.length === 0 ? (
              <p style={styles.emptyText}>No food items logged for this date. Search above to add meals.</p>
            ) : (
              <div style={styles.loggedList}>
                {logs.map((item) => (
                  <div key={item.id} style={styles.loggedItem}>
                    <div style={styles.loggedInfo}>
                      <div style={styles.loggedHeader}>
                        <strong style={styles.loggedName}>{item.name}</strong>
                        <span style={styles.loggedGrams}>({item.grams}g)</span>
                      </div>
                      <div style={styles.loggedMacros}>
                        <span>{item.calories} kcal</span> •{' '}
                        <span>{item.protein}g protein</span> •{' '}
                        <span>{item.carbs}g carbs</span> •{' '}
                        <span>{item.fat}g fat</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteLog(item.id)}
                      style={styles.deleteBtn}
                      title="Remove item"
                    >
                      ✕
                    </button>
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
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '24px 20px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
    flexWrap: 'wrap',
    gap: '16px',
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
  dateSelector: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  dateLabel: {
    fontWeight: '600',
    color: '#475569',
    fontSize: '14px',
  },
  dateInput: {
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    fontSize: '14px',
    outline: 'none',
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
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  summaryCard: {
    backgroundColor: '#ffffff',
    borderRadius: '10px',
    padding: '16px 20px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  summaryLabel: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  summaryValue: {
    fontSize: '26px',
    fontWeight: '800',
    color: '#0f172a',
  },
  unit: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#94a3b8',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
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
  searchForm: {
    display: 'flex',
    gap: '10px',
    marginBottom: '16px',
  },
  searchInput: {
    flex: 1,
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    fontSize: '15px',
    outline: 'none',
  },
  searchBtn: {
    padding: '10px 20px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  resultsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    maxHeight: '450px',
    overflowY: 'auto',
  },
  resultsHeading: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#64748b',
    margin: '8px 0 4px 0',
  },
  foodItem: {
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
  },
  foodInfo: {
    flex: 1,
  },
  foodName: {
    fontSize: '14px',
    color: '#0f172a',
    display: 'block',
    marginBottom: '4px',
  },
  foodMacros: {
    fontSize: '12px',
    color: '#64748b',
  },
  perServing: {
    color: '#94a3b8',
    fontSize: '11px',
  },
  addActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  gramsInput: {
    width: '60px',
    padding: '6px 8px',
    borderRadius: '4px',
    border: '1px solid #cbd5e1',
    fontSize: '13px',
    textAlign: 'center',
  },
  gramsUnit: {
    fontSize: '12px',
    color: '#64748b',
  },
  addBtn: {
    padding: '6px 12px',
    backgroundColor: '#10b981',
    color: '#ffffff',
    border: 'none',
    borderRadius: '4px',
    fontWeight: '600',
    fontSize: '13px',
    cursor: 'pointer',
  },
  loggedList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  loggedItem: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fafafa',
  },
  loggedInfo: {
    flex: 1,
  },
  loggedHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '4px',
  },
  loggedName: {
    fontSize: '14px',
    color: '#1e293b',
  },
  loggedGrams: {
    fontSize: '12px',
    color: '#64748b',
  },
  loggedMacros: {
    fontSize: '12px',
    color: '#475569',
  },
  deleteBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '4px 8px',
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: '14px',
  },
};
