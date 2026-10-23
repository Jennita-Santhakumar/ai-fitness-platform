import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Link } from 'react-router-dom';

export const Dashboard = () => {
  const { user } = useAuth();

  return (
    <div style={styles.page}>
      <Navbar />
      <div style={styles.container}>
        <div style={styles.headerCard}>
          <h1 style={styles.heading}>Welcome back, {user?.email || 'Athlete'}! 👋</h1>
          <p style={styles.lead}>
            Your AI-powered training hub is active. Generate plans, log workouts, and track daily nutrition.
          </p>
        </div>

        <div style={styles.grid}>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>🏋️ Workout Plans</h3>
            <p style={styles.cardText}>
              Generate custom multi-week training plans with memory-augmented AI coaching.
            </p>
            <Link to="/plans" style={styles.cardBtn}>Explore Plans</Link>
          </div>

          <div style={styles.card}>
            <h3 style={styles.cardTitle}>⏱️ Training Sessions</h3>
            <p style={styles.cardText}>
              Log completed workouts and sync activities automatically with Strava.
            </p>
            <Link to="/sessions" style={styles.cardBtn}>View Sessions</Link>
          </div>

          <div style={styles.card}>
            <h3 style={styles.cardTitle}>🥗 Nutrition & Macros</h3>
            <p style={styles.cardText}>
              Search the USDA FoodData Central database and track your daily calorie and macro goals.
            </p>
            <Link to="/nutrition" style={styles.cardBtn}>Track Nutrition</Link>
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
    padding: '32px 20px',
  },
  headerCard: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    padding: '32px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    marginBottom: '28px',
  },
  heading: {
    margin: '0 0 10px 0',
    fontSize: '28px',
    fontWeight: '800',
    color: '#0f172a',
  },
  lead: {
    margin: 0,
    fontSize: '16px',
    color: '#64748b',
    lineHeight: '1.5',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '24px',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  },
  cardTitle: {
    margin: '0 0 12px 0',
    fontSize: '20px',
    fontWeight: '700',
    color: '#1e293b',
  },
  cardText: {
    margin: '0 0 20px 0',
    fontSize: '15px',
    color: '#64748b',
    lineHeight: '1.5',
    flexGrow: 1,
  },
  cardBtn: {
    display: 'inline-block',
    textAlign: 'center',
    padding: '10px 16px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    textDecoration: 'none',
    borderRadius: '6px',
    fontWeight: '600',
    fontSize: '14px',
  },
};
