import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'app.crewlog.mobile',
  appName: 'CrewLog',
  webDir: 'public',
  server: {
    url: process.env.CREWLOG_WEB_URL || process.env.APP_BASE_URL || 'https://crewlog.app',
    cleartext: false,
    allowNavigation: [
      'crewlog.app',
      '*.crewlog.app',
      '*.replit.dev',
      '*.stripe.com',
      'checkout.stripe.com',
      'billing.stripe.com',
      'js.stripe.com',
    ],
  },
  plugins: {
    Browser: {
      presentationStyle: 'fullscreen',
    },
    Geolocation: {},
    Camera: {},
  },
  ios: {
    contentInset: 'automatic',
    allowsLinkPreview: false,
    scrollEnabled: true,
    scheme: 'CrewLog',
  },
};

export default config;
