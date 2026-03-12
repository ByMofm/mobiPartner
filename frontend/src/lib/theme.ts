import { createTheme } from "@mui/material/styles";

const sharedTypography = {
  fontFamily: '"Inter", "Roboto", sans-serif',
  h5: { fontWeight: 600 },
  h6: { fontWeight: 600 },
};

const sharedComponents = {
  MuiCard: {
    defaultProps: { elevation: 1 as const },
    styleOverrides: {
      root: {
        transition: "transform 0.15s, box-shadow 0.15s",
      },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: { fontWeight: 500 },
    },
  },
  MuiButton: {
    styleOverrides: {
      containedSecondary: {
        color: "#FFFFFF",
      },
    },
  },
};

export const lightTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#FFE600",
      contrastText: "#1A1A2E",
    },
    secondary: {
      main: "#3483FA",
    },
    background: {
      default: "#EBEBEB",
      paper: "#FFFFFF",
    },
  },
  typography: sharedTypography,
  shape: {
    borderRadius: 8,
  },
  components: {
    ...sharedComponents,
    MuiPaper: {
      styleOverrides: {
        root: {
          border: "1px solid rgba(0,0,0,0.06)",
        },
      },
    },
  },
});

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#FFE600",
      contrastText: "#1A1A2E",
    },
    secondary: {
      main: "#3483FA",
    },
    background: {
      default: "#1A1A2E",
      paper: "#16213E",
    },
  },
  typography: sharedTypography,
  shape: {
    borderRadius: 8,
  },
  components: {
    ...sharedComponents,
    MuiPaper: {
      styleOverrides: {
        root: {
          border: "1px solid rgba(255,255,255,0.06)",
        },
      },
    },
  },
});
