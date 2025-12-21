/**
 * Desktop toolbar with health indicator, notifications, and user menu
 * Positioned in top-right corner, visible only on desktop (lg+)
 */

'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { User, LogOut, KeyRound, Circle, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { NotificationBell } from '@/components/notifications';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

export function DesktopToolbar() {
  const router = useRouter();
  const { user, logout, isAuthenticated } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      toast.success('Logged out successfully');
      router.push('/login');
    } catch (error) {
      console.error('Logout error:', error);
      router.push('/login');
    }
  };

  return (
    <div className="fixed top-4 right-4 z-50 hidden lg:flex items-center gap-2">
      {/* System Status Indicator */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-background border shadow-sm"
              role="status"
              aria-label="System status: Healthy"
            >
              <Circle className="h-2 w-2 fill-green-500 text-green-500" aria-hidden="true" />
              <span className="text-xs font-medium">Healthy</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p className="text-xs">System Status: Healthy</p>
            <p className="text-xs text-muted-foreground">All services operational</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Notification Bell */}
      <div className="bg-background border rounded-md shadow-sm">
        <NotificationBell />
      </div>

      {/* User Menu */}
      {isAuthenticated && user && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 shadow-sm"
              aria-label={`User menu for ${user.username}`}
              aria-haspopup="menu"
            >
              <User className="h-4 w-4" aria-hidden="true" />
              <span className="text-sm">{user.username}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium">{user.username}</p>
                <p className="text-xs text-muted-foreground">Logged in</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings" className="flex items-center gap-2 cursor-pointer">
                <Settings className="h-4 w-4" aria-hidden="true" />
                Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/settings?tab=security" className="flex items-center gap-2 cursor-pointer">
                <KeyRound className="h-4 w-4" aria-hidden="true" />
                Change Password
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleLogout}
              className="flex items-center gap-2 cursor-pointer text-red-600 dark:text-red-400"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
