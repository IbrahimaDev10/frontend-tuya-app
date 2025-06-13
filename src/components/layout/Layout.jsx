import { useContext } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header/Header';
import Sidebar from './Sidebar/Sidebar';
import { MyContext } from '../../App';

function Layout() {
  const { isHideSidebarAndHeader, toggleSidebar } = useContext(MyContext);

  return (
    <>
      {isHideSidebarAndHeader !== false && <Header />}
      <div className="main d-flex">
        {isHideSidebarAndHeader !== false && (
          <div className={`sidebarWrapper ${toggleSidebar ? 'visible' : 'hide'}`}>
            <Sidebar />
          </div>
        )}
        <div className="content">
          <Outlet />
        </div>
      </div>
    </>
  );
}

export default Layout;
