"use client";

import { useContext } from "react";
import IconButton from "@mui/material/IconButton";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { ColorModeContext } from "./ThemeRegistry";

export default function ThemeToggle() {
  const { toggleColorMode, mode } = useContext(ColorModeContext);

  return (
    <IconButton onClick={toggleColorMode} color="inherit" title={mode === "dark" ? "Modo claro" : "Modo oscuro"}>
      {mode === "dark" ? <Brightness7Icon /> : <Brightness4Icon />}
    </IconButton>
  );
}
