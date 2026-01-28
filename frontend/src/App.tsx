import { HashRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { MainLayout } from '@/components/Layout';
import { Dashboard } from '@/pages';
import 'antd/dist/reset.css';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <HashRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
          </Route>
        </Routes>
      </HashRouter>
    </ConfigProvider>
  );
}

export default App;
