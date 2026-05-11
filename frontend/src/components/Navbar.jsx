import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { FileText, Menu, X } from 'lucide-react'
import ThemeToggle from './ThemeToggle'

export default function Navbar({ theme, toggleTheme }) {
  const [open, setOpen] = useState(false)

  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors ${
      isActive
        ? 'text-brand-600 dark:text-brand-400'
        : 'text-brand-700 dark:text-gray-400 hover:text-brand-600 dark:hover:text-gray-200'
    }`

  return (
    <header className="fixed top-0 inset-x-0 z-40 backdrop-blur-md bg-white/80 dark:bg-gray-950/90 border-b border-brand-100 dark:border-gray-800">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-6">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 bg-brand-600 dark:bg-brand-500 rounded-lg flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-brand-900 dark:text-white text-lg">ScriptSense</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          <NavLink to="/" end className={linkClass}>Home</NavLink>
          <NavLink to="/app" className={linkClass}>Convert</NavLink>
          <NavLink to="/history" className={linkClass}>History</NavLink>
        </nav>

        <div className="flex items-center gap-3">
          <ThemeToggle theme={theme} toggle={toggleTheme} />

          {/* Mobile hamburger */}
          <button
            className="md:hidden w-9 h-9 flex items-center justify-center rounded-xl
                       text-brand-600 dark:text-gray-400 hover:bg-brand-50 dark:hover:bg-gray-800"
            onClick={() => setOpen(o => !o)}
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t border-brand-100 dark:border-gray-800 bg-white dark:bg-gray-950 px-4 py-4 flex flex-col gap-3">
          <NavLink to="/" end className={linkClass} onClick={() => setOpen(false)}>Home</NavLink>
          <NavLink to="/app" className={linkClass} onClick={() => setOpen(false)}>Convert</NavLink>
          <NavLink to="/history" className={linkClass} onClick={() => setOpen(false)}>History</NavLink>
          <Link to="/app" className="btn-primary mt-1 w-full justify-center" onClick={() => setOpen(false)}>
            Try It Now
          </Link>
        </div>
      )}
    </header>
  )
}
