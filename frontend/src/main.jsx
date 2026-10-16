import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = '/api';
const STATUSES = ['PENDING', 'IN_PROGRESS', 'SUBMITTED'];
const NEXT_STATUS = { PENDING: 'IN_PROGRESS', IN_PROGRESS: 'SUBMITTED', SUBMITTED: 'PENDING' };

const label = (s) => s.replace('_', ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());

function daysLeft(due) {
  if (!due) return null;
  const today = new Date(new Date().toDateString());
  return Math.round((new Date(due) - today) / 86400000);
}

function dueText(a) {
  const d = daysLeft(a.due_date);
  if (d === null) return 'No due date';
  if (a.status === 'SUBMITTED') return `Due ${a.due_date}`;
  if (d < 0) return `Overdue by ${-d} day${d === -1 ? '' : 's'}`;
  if (d === 0) return 'Due today';
  return `Due in ${d} day${d === 1 ? '' : 's'}`;
}

function App() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({ total: 0, pending: 0, inProgress: 0, submitted: 0, overdue: 0 });
  const [filter, setFilter] = useState('ALL');
  const [course, setCourse] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setError('');
      const [list, summary] = await Promise.all([fetch(`${API}/assignments`), fetch(`${API}/assignments/stats`)]);
      if (!list.ok || !summary.ok) throw Error('Backend unavailable');
      setItems(await list.json());
      setStats(await summary.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const courses = [...new Set(items.map((a) => a.course))].sort();
  const visible = items
    .filter((a) => filter === 'ALL' || a.status === filter)
    .filter((a) => !course || a.course === course);
  const upcoming = items
    .filter((a) => a.status !== 'SUBMITTED' && a.due_date)
    .slice(0, 5);

  const advance = async (a) => {
    await fetch(`${API}/assignments/${a.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: NEXT_STATUS[a.status] }),
    });
    load();
  };

  const remove = async (a) => {
    if (!window.confirm(`Delete "${a.title}"?`)) return;
    await fetch(`${API}/assignments/${a.id}`, { method: 'DELETE' });
    load();
  };

  const create = async (e) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await fetch(`${API}/assignments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: f.get('title'),
        course: f.get('course'),
        notes: f.get('notes'),
        due_date: f.get('due_date') || null,
        priority: f.get('priority'),
      }),
    });
    e.currentTarget.reset();
    setShowForm(false);
    load();
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div><b>StudyDesk</b><small>Assignment tracker</small></div>
        </div>
        <nav>
          <a className="active">▦ <span>Dashboard</span></a>
          {courses.map((c) => (
            <a key={c} onClick={() => setCourse(course === c ? '' : c)} className={course === c ? 'active' : ''}>◫ <span>{c}</span></a>
          ))}
        </nav>
        <div className="side-bottom">
          <div className="profile">
            <div className="avatar">VK</div>
            <div><b>Varshitha Kolupuri</b><small>SST · 10271</small></div>
          </div>
        </div>
      </aside>

      <main className="main">
        <header>
          <div>
            <p className="eyebrow">SEMESTER 5 / ASSIGNMENTS</p>
            <h1>{stats.overdue ? `${stats.overdue} overdue, ` : ''}{stats.pending + stats.inProgress} still open</h1>
            <p className="muted">Everything due across your courses, soonest deadline first.</p>
          </div>
          <button className="primary" onClick={() => setShowForm(true)}>＋ Add assignment</button>
        </header>

        {error && <div className="alert">⚠ {error}. Start the backend and PostgreSQL, then refresh.</div>}

        <section className="stats">
          <Stat label="Pending" value={stats.pending} icon="○" />
          <Stat label="In progress" value={stats.inProgress} icon="◔" />
          <Stat label="Submitted" value={stats.submitted} icon="✓" />
          <Stat label="Overdue" value={stats.overdue} icon="!" />
        </section>

        <section className="content-grid">
          <div className="panel tasks-panel">
            <div className="panel-head">
              <div>
                <h2>{course || 'All courses'}</h2>
                <p className="muted">{visible.length} of {stats.total} assignments</p>
              </div>
              <div className="filters">
                {['ALL', ...STATUSES].map((x) => (
                  <button className={filter === x ? 'selected' : ''} onClick={() => setFilter(x)} key={x}>
                    {x === 'ALL' ? 'All' : label(x)}
                  </button>
                ))}
              </div>
            </div>
            {loading ? <div className="empty">Loading assignments…</div> : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Assignment</th><th>Course</th><th>Due</th><th>Priority</th><th>Status</th><th></th></tr>
                  </thead>
                  <tbody>
                    {visible.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <div className="task-title">
                            <span className={`dot ${a.status.toLowerCase()}`}></span>
                            <div><b>{a.title}</b><small>{a.notes}</small></div>
                          </div>
                        </td>
                        <td>{a.course}</td>
                        <td className={daysLeft(a.due_date) < 0 && a.status !== 'SUBMITTED' ? 'late' : ''}>{dueText(a)}</td>
                        <td><span className={`priority ${a.priority.toLowerCase()}`}>{a.priority}</span></td>
                        <td><span className={`status ${a.status.toLowerCase()}`}>{label(a.status)}</span></td>
                        <td>
                          <button className="icon-btn" onClick={() => advance(a)} title="Move to next status">↻</button>{' '}
                          <button className="icon-btn" onClick={() => remove(a)} title="Delete">✕</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!visible.length && <div className="empty">Nothing here. Add an assignment to get started.</div>}
              </div>
            )}
          </div>

          <aside className="panel activity">
            <div className="panel-head">
              <div><h2>Coming up</h2><p className="muted">Next deadlines that aren't submitted yet.</p></div>
            </div>
            {upcoming.map((a) => (
              <div className="activity-row" key={a.id}>
                <span className="activity-icon">{daysLeft(a.due_date) < 0 ? '!' : '◷'}</span>
                <div><b>{a.title}</b><small>{a.course} · {dueText(a)}</small></div>
              </div>
            ))}
            {!upcoming.length && <div className="empty">No open deadlines.</div>}
          </aside>
        </section>

        {showForm && (
          <div className="modal-backdrop">
            <form className="modal" onSubmit={create}>
              <div className="modal-head">
                <div><p className="eyebrow">NEW ASSIGNMENT</p><h2>Add an assignment</h2></div>
                <button type="button" className="close" onClick={() => setShowForm(false)}>×</button>
              </div>
              <label>Title<input name="title" required placeholder="e.g. Terraform VPC lab" /></label>
              <div className="form-row">
                <label>Course<input name="course" required list="course-list" placeholder="e.g. DevOps" /></label>
                <label>Due date<input name="due_date" type="date" /></label>
              </div>
              <datalist id="course-list">{courses.map((c) => <option key={c} value={c} />)}</datalist>
              <label>Notes<textarea name="notes" placeholder="Submission link, rubric points, anything to remember" /></label>
              <label>Priority
                <select name="priority" defaultValue="MEDIUM"><option>LOW</option><option>MEDIUM</option><option>HIGH</option></select>
              </label>
              <button className="primary full">Save assignment</button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value, icon }) {
  return (
    <div className="stat">
      <div className="stat-icon">{icon}</div>
      <div><small>{label}</small><strong>{value}</strong></div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
