// components/Alerts/AlertTest.jsx
import React, { useState } from 'react'
import AlertService from '../../services/alertService'
import Button from '../Button'

const AlertTest = () => {
  const [testResults, setTestResults] = useState(null)
  const [loading, setLoading] = useState(false)

  const runTests = async () => {
    setLoading(true)
    try {
      const [
        healthResponse,
        testResponse,
        importResponse
      ] = await Promise.all([
        AlertService.obtenirSanteService(),
        AlertService.testerService(),
        AlertService.testerImportModeles()
      ])

      setTestResults({
        health: healthResponse.data,
        test: testResponse.data,
        import: importResponse.data
      })
    } catch (error) {
      console.error('Erreur tests alertes:', error)
      setTestResults({ error: error.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="alert-test">
      <h3>🧪 Test du système d'alertes</h3>
      
      <Button
        variant="primary"
        onClick={runTests}
        loading={loading}
      >
        Lancer les tests
      </Button>

      {testResults && (
        <div className="test-results">
          <h4>Résultats des tests :</h4>
          <pre>{JSON.stringify(testResults, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

export default AlertTest
