// Materiales del tiquete de pesaje. rateKey conecta cada grupo con las
// tarifas por material administradas en Reglas de EcoPuntos.
export const intakeCatalog = [
  { id: 'papel', name: 'Cartón y papel', icon: 'paper', items: [
    { name: 'Plegadiza', rateKey: 'Cartón' },
    { name: 'Cartón', rateKey: 'Cartón' },
    { name: 'Papel', rateKey: 'Papel' },
    { name: 'Archivo', rateKey: 'Papel' },
    { name: 'Periódico', rateKey: 'Papel' },
    { name: 'Kraft', rateKey: 'Papel' },
    { name: 'Tetrapack', rateKey: 'Cartón' },
  ] },
  { id: 'plasticos', name: 'Plásticos', icon: 'plastic', items: [
    { name: 'Plástico de hoja', rateKey: 'Plástico' },
    { name: 'Plástico soplado', rateKey: 'Plástico' },
    { name: 'Plástico chibron', rateKey: 'Plástico' },
    { name: 'Plástico thermo', rateKey: 'Plástico' },
    { name: 'Plástico PET', rateKey: 'Plástico' },
    { name: 'Plástico PET color', rateKey: 'Plástico' },
    { name: 'Bolsa de fibra', rateKey: 'Plástico' },
    { name: 'Pasta', rateKey: 'Plástico' },
    { name: 'Canecas pequeñas', rateKey: 'Plástico' },
  ] },
  { id: 'metales', name: 'Metales', icon: 'metal', items: [
    { name: 'Hierro', rateKey: 'Metal' },
    { name: 'Latón', rateKey: 'Metal' },
    { name: 'Aluminio delgado', rateKey: 'Metal' },
    { name: 'Aluminio grueso', rateKey: 'Metal' },
    { name: 'Radiador mixto', rateKey: 'Metal' },
  ] },
  { id: 'vidrio', name: 'Vidrio', icon: 'glass', items: [
    { name: 'Vidrio', rateKey: 'Vidrio' },
  ] },
  { id: 'otros', name: 'Otros', icon: 'other', items: [
    { name: 'Otros aprovechables', rateKey: 'Otros aprovechables' },
  ] },
] as const
