import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import TaskDetailsPage from './pages/TaskDetailsPage';
import SessionsPage from './pages/SessionsPage';
import { SessionProvider } from './contexts/SessionContext';

function App() {
  return (
    <Router>
      <SessionProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/task-details" element={<TaskDetailsPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
          </Routes>
        </Layout>
      </SessionProvider>
    </Router>
  );
}

export default App;
