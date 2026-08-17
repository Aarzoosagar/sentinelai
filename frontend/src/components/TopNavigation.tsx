import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, User as UserIcon, LogOut } from "lucide-react";
import { useAuth } from "@/store/authStore";

export function TopNavigation() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchValue.trim()) {
      navigate(`/findings?search=${encodeURIComponent(searchValue.trim())}`);
    }
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-bg px-6">
      <form onSubmit={handleSearch} className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-secondary" />
        <input
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          placeholder="Search findings, resources, reports..."
          className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-3 text-sm placeholder:text-text-secondary/60 focus:border-accent-blue focus:outline-none"
        />
      </form>

      <div className="relative">
        <button
          onClick={() => setMenuOpen((o) => !o)}
          className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-text-secondary hover:bg-card"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-blue/20 text-accent-blue">
            <UserIcon className="h-4 w-4" />
          </span>
          <span className="hidden sm:inline">{user?.full_name}</span>
        </button>
        {menuOpen && (
          <div className="absolute right-0 mt-2 w-48 rounded-lg border border-border bg-card py-1 shadow-card">
            <button
              onClick={() => {
                setMenuOpen(false);
                navigate("/profile");
              }}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-text-secondary hover:bg-white/5 hover:text-text-primary"
            >
              <UserIcon className="h-4 w-4" /> Profile
            </button>
            <button
              onClick={logout}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-accent-red hover:bg-accent-red/10"
            >
              <LogOut className="h-4 w-4" /> Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
