"use client";

import { useContext } from "react";
import Link from "next/link";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Badge from "@mui/material/Badge";
import Divider from "@mui/material/Divider";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/Menu";
import HomeIcon from "@mui/icons-material/Home";
import ApartmentIcon from "@mui/icons-material/Apartment";
import DashboardIcon from "@mui/icons-material/Dashboard";
import FavoriteIcon from "@mui/icons-material/Favorite";
import { useState } from "react";
import { useRouter } from "next/navigation";
import LogoutIcon from "@mui/icons-material/Logout";
import ThemeToggle from "./ThemeToggle";
import { useFavorites } from "@/contexts/FavoritesContext";

const NAV_LINKS = [
  { href: "/properties", label: "Propiedades", icon: <ApartmentIcon /> },
  { href: "/dashboard", label: "Dashboard", icon: <DashboardIcon /> },
  { href: "/favorites", label: "Favoritos", icon: <FavoriteIcon /> },
];

export default function NavBar() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { favorites } = useFavorites();
  const router = useRouter();

  const handleLogout = async () => {
    await fetch("/api/auth", { method: "DELETE" });
    router.push("/login");
    router.refresh();
  };

  return (
    <AppBar position="sticky" color="default" elevation={1}>
      <Toolbar>
        <Typography
          variant="h6"
          component={Link}
          href="/"
          color="secondary"
          sx={{ fontWeight: "bold", textDecoration: "none", mr: 3 }}
        >
          mobiPartner
        </Typography>

        {isMobile ? (
          <>
            <Box sx={{ flexGrow: 1 }} />
            <ThemeToggle />
            <IconButton color="inherit" onClick={handleLogout} title="Cerrar sesion" sx={{ mr: 0.5 }}>
              <LogoutIcon />
            </IconButton>
            <IconButton color="inherit" onClick={() => setDrawerOpen(true)} edge="end">
              <MenuIcon />
            </IconButton>
            <Drawer anchor="right" open={drawerOpen} onClose={() => setDrawerOpen(false)}>
              <Box sx={{ width: 260, pt: 2 }}>
                <Typography variant="h6" color="secondary" sx={{ fontWeight: "bold", px: 2, pb: 1 }}>
                  mobiPartner
                </Typography>
                <Divider />
                <List>
                  {NAV_LINKS.map((link) => (
                    <ListItemButton
                      key={link.href}
                      component={Link}
                      href={link.href}
                      onClick={() => setDrawerOpen(false)}
                    >
                      <ListItemIcon>
                        {link.label === "Favoritos" ? (
                          <Badge badgeContent={favorites.length} color="error" max={99}>
                            {link.icon}
                          </Badge>
                        ) : (
                          link.icon
                        )}
                      </ListItemIcon>
                      <ListItemText primary={link.label} />
                    </ListItemButton>
                  ))}
                </List>
              </Box>
            </Drawer>
          </>
        ) : (
          <>
            <Box sx={{ display: "flex", gap: 1, flexGrow: 1 }}>
              <Button component={Link} href="/properties" color="inherit">
                Propiedades
              </Button>
              <Button component={Link} href="/dashboard" color="inherit">
                Dashboard
              </Button>
              <Button component={Link} href="/favorites" color="inherit" startIcon={
                <Badge badgeContent={favorites.length} color="error" max={99}>
                  <FavoriteIcon fontSize="small" />
                </Badge>
              }>
                Favoritos
              </Button>
            </Box>
            <ThemeToggle />
            <IconButton color="inherit" onClick={handleLogout} title="Cerrar sesion" sx={{ ml: 1 }}>
              <LogoutIcon fontSize="small" />
            </IconButton>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
}
