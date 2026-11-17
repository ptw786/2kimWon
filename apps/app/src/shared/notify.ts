// 벨이 울릴 때 화면이 가려져 있으면 시스템 알림으로 알린다. 앱이 열려 있는 동안(다른 화면·탭 포함)만 동작한다.
export type NotifyPermission = NotificationPermission | 'unsupported'

const TAG = 'ansimon-ring'

export function notifyPermission(): NotifyPermission {
  return typeof Notification === 'undefined' ? 'unsupported' : Notification.permission
}

export async function requestNotifyPermission(): Promise<NotifyPermission> {
  if (typeof Notification === 'undefined') return 'unsupported'
  try { return await Notification.requestPermission() } catch { return Notification.permission }
}

export async function showRingNotification(): Promise<void> {
  if (notifyPermission() !== 'granted') return
  const options = {
    body: '눌러서 받아 주세요',
    tag: TAG,
    requireInteraction: true,
    vibrate: [400, 200, 400, 200, 400],
    icon: '/icons/icon-192.png',
  } as NotificationOptions
  try {
    const reg = 'serviceWorker' in navigator ? await navigator.serviceWorker.getRegistration() : undefined
    if (reg) { await reg.showNotification('안심온 전화가 왔어요', options); return }
    new Notification('안심온 전화가 왔어요', options)
  } catch { /* 알림을 못 띄워도 벨 화면은 그대로 */ }
}

export async function closeRingNotification(): Promise<void> {
  try {
    const reg = 'serviceWorker' in navigator ? await navigator.serviceWorker.getRegistration() : undefined
    const list = (await reg?.getNotifications({ tag: TAG })) ?? []
    list.forEach((n) => n.close())
  } catch { /* 없으면 그만 */ }
}
