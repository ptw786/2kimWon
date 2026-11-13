import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { CallProvider, useCall } from '../features/call/index.ts'
import { CallScreen, DoneScreen, RingScreen } from '../features/call/index.ts'
import { Home } from '../features/home/index.ts'
import { ByCode, Picker } from '../features/identity/index.ts'
import { Records } from '../features/records/index.ts'
import { Settings } from '../features/settings/index.ts'
import { SettingsProvider, useSettings } from '../shared/settings.tsx'

function Shell() {
  const { settings } = useSettings()
  const { phase } = useCall()
  if (phase === 'ringing' || phase === 'answering') return <RingScreen />
  if (phase === 'talk') return <CallScreen />
  if (phase === 'done') return <DoneScreen />
  return (
    <Routes>
      <Route path="/r/:code" element={<ByCode />} />
      {settings.residentId === null ? (
        <Route path="*" element={<Picker />} />
      ) : (
        <>
          <Route path="/" element={<Home />} />
          <Route path="/records" element={<Records />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </>
      )}
    </Routes>
  )
}

export function App() {
  return (
    <SettingsProvider>
      <BrowserRouter>
        <CallProvider>
          <Shell />
        </CallProvider>
      </BrowserRouter>
    </SettingsProvider>
  )
}
