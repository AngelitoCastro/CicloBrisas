import { defaultPointRule, type EcoPointRule, type EcoPointRules, type Flow, type Generator } from '../types'

export const pointRuleFlows = ['organico', 'reciclable'] as const satisfies readonly Flow[]
export const pointRuleGenerators = ['Hogar', 'Comercio'] as const satisfies readonly Generator[]
export const pointRuleFields = ['base', 'perKg'] as const
export const maxPointRuleValue = 99_999_999.99

export function isValidPointAmount(value: unknown): value is number {
    return typeof value === 'number' && Number.isFinite(value) &&
        value >= 0 && value <= maxPointRuleValue && Number(value.toFixed(2)) === value
}

export function loadPointRules(saved?: Partial<Record<Flow, Partial<Record<Generator, Partial<EcoPointRule>>>>>): EcoPointRules {
    const rules: EcoPointRules = {
        organico: { Hogar: { ...defaultPointRule }, Comercio: { ...defaultPointRule } },
        reciclable: { Hogar: { ...defaultPointRule }, Comercio: { ...defaultPointRule } },
    }
    for (const flow of pointRuleFlows) {
        for (const generator of pointRuleGenerators) {
            for (const field of pointRuleFields) {
                const value = saved?.[flow]?.[generator]?.[field]
                if (isValidPointAmount(value)) rules[flow][generator][field] = value
            }
        }
    }
    return rules
}

export function calculateEcoPoints(weightHundredths: number, rule: EcoPointRule) {
    const baseHundredths = Math.round(rule.base * 100)
    const rateHundredths = Math.round(rule.perKg * 100)
    return (baseHundredths + Math.round(weightHundredths * rateHundredths / 100)) / 100
}
