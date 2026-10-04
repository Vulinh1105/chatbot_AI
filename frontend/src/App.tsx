import AppRoutes from "./routes/AppRoutes";
import AuthInitializer from "./components/common/AuthInitializer";
import "./App.css";

function App() {
  return (
    <>
      <AuthInitializer />
      <AppRoutes />
    </>
  );
}

export default App;