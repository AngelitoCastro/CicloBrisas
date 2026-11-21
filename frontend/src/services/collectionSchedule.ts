import type { Schedule } from '../types'

const bogotaTime = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
})
const clockTime = /^([01]\d|2[0-3]):[0-5]\d$/

type CollectionClock = { today: string; tomorrow: string; time: string }
type Slot = Schedule['slots'][number]

function addDays(date: string, days: number) {
    const day = new Date(date + 'T00:00:00Z')
    day.setUTCDate(day.getUTCDate() + days)
    return day.toISOString().slice(0, 10)
}

export function getCollectionClock(now = new Date()): CollectionClock {
    const parts = Object.fromEntries(bogotaTime.formatToParts(now).map(part => [part.type, part.value]))
    const today = parts.year + '-' + parts.month + '-' + parts.day
    return { today, tomorrow: addDays(today, 1), time: parts.hour + ':' + parts.minute }
}

function isConfiguredDay(schedule: Schedule, date: string, clock: CollectionClock) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || date < clock.today) return false
    const day = new Date(date + 'T00:00:00Z')
    return Number.isFinite(day.getTime()) && day.toISOString().slice(0, 10) === date && schedule.days.includes(day.getUTCDay())
}

function isUsableSlot(slot: Slot, date: string, clock: CollectionClock) {
    return clockTime.test(slot.start) && clockTime.test(slot.end) && slot.start < slot.end &&
        (date > clock.today || slot.end > clock.time)
}

function availableSlots(schedule: Schedule, date: string, clock: CollectionClock) {
    return isConfiguredDay(schedule, date, clock) ? schedule.slots.filter(slot => isUsableSlot(slot, date, clock)) : []
}

export const collectionSlotKey = (slot: Slot) => slot.start + ' – ' + slot.end

export function isCollectionSlotAvailable(schedule: Schedule, date: string, slotKey: string, clock: CollectionClock) {
    return availableSlots(schedule, date, clock).some(slot => collectionSlotKey(slot) === slotKey)
}

export function isCollectionDayAvailable(schedule: Schedule, date: string, clock: CollectionClock) {
    return availableSlots(schedule, date, clock).length > 0
}

export function getNextCollectionAvailability(schedule: Schedule, clock: CollectionClock) {
    for (let offset = 0; offset <= 7; offset++) {
        const date = addDays(clock.today, offset)
        const [slot] = availableSlots(schedule, date, clock).sort((a, b) => a.start.localeCompare(b.start) || a.end.localeCompare(b.end))
        if (slot) return { date, slot: collectionSlotKey(slot) }
    }
    return { date: '', slot: '' }
}
