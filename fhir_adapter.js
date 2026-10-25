/**
 * HL7 FHIR v4 Interoperability Adapter
 * Ruang Rawat Inap Enggang Gading 2 - RSUD Dr. Soedarso Pontianak
 * Standards: HL7 FHIR Release 4 (v4.0.1) & Kemenkes SatuSehat Profile
 */

(function (global) {
  'use strict';

  const FHIRAdapter = {
    /**
     * Konversi pasien Ruang Enggang Gading 2 ke HL7 FHIR v4 Patient Resource
     * @param {Object} pt - Objek pasien dari dashboard_data.json
     * @returns {Object} FHIR Patient Resource
     */
    toFhirPatient: function (pt) {
      if (!pt) return null;
      const mrNo = (pt.mrNo || '').trim();
      const patientId = mrNo && mrNo !== '-' ? `pt-mrn-${mrNo.replace(/\D/g, '')}` : `pt-${encodeURIComponent(pt.name || 'anon')}`;
      
      const genderCode = pt.gender === 'L' ? 'male' : (pt.gender === 'P' ? 'female' : 'unknown');

      return {
        resourceType: 'Patient',
        id: patientId,
        meta: {
          profile: ['https://fhir.kemkes.go.id/r4/StructureDefinition/Patient'],
          lastUpdated: new Date().toISOString()
        },
        identifier: [
          {
            use: 'official',
            type: {
              coding: [
                {
                  system: 'http://terminology.hl7.org/CodeSystem/v2-0203',
                  code: 'MR',
                  display: 'Medical Record Number'
                }
              ]
            },
            system: 'http://sys-ids.kemkes.go.id/mrn/soedarso',
            value: mrNo || '-'
          }
        ],
        active: pt.isActive !== false,
        name: [
          {
            use: 'official',
            text: pt.name || 'Tanpa Nama'
          }
        ],
        gender: genderCode,
        managingOrganization: {
          reference: 'Organization/soedarso-pontianak',
          display: 'RSUD Dr. Soedarso Pontianak'
        }
      };
    },

    /**
     * Konversi episode rawat inap ke HL7 FHIR v4 Encounter Resource
     * @param {Object} pt - Objek pasien
     * @param {string} dateStr - Tanggal sensus / encounter (YYYY-MM-DD)
     * @returns {Object} FHIR Encounter Resource
     */
    toFhirEncounter: function (pt, dateStr) {
      if (!pt) return null;
      const mrNo = (pt.mrNo || '').trim();
      const patientRef = mrNo && mrNo !== '-' ? `Patient/pt-mrn-${mrNo.replace(/\D/g, '')}` : `Patient/pt-${encodeURIComponent(pt.name || 'anon')}`;
      const encounterId = `enc-${pt.room || 'EG2'}-${pt.bed || '0'}-${(dateStr || 'current').replace(/-/g, '')}`;

      const status = pt.isDeceased ? 'finished' : (pt.isDischargedToday ? 'finished' : 'in-progress');

      return {
        resourceType: 'Encounter',
        id: encounterId,
        meta: {
          profile: ['https://fhir.kemkes.go.id/r4/StructureDefinition/Encounter'],
          lastUpdated: new Date().toISOString()
        },
        identifier: [
          {
            system: 'http://sys-ids.kemkes.go.id/encounter/soedarso',
            value: `${pt.room}-B${pt.bed}-${pt.admissionDate || ''}`
          }
        ],
        status: status,
        class: {
          system: 'http://terminology.hl7.org/CodeSystem/v3-ActCode',
          code: 'IMP',
          display: 'inpatient encounter'
        },
        subject: {
          reference: patientRef,
          display: pt.name
        },
        participant: [
          {
            type: [
              {
                coding: [
                  {
                    system: 'http://terminology.hl7.org/CodeSystem/v3-ParticipationType',
                    code: 'ATND',
                    display: 'attender'
                  }
                ]
              }
            ],
            individual: {
              display: pt.doctorPrimary || pt.doctor || 'DPJP Ruang Rawat'
            }
          }
        ],
        period: {
          start: pt.admissionDate ? `${pt.admissionDate}T07:00:00+07:00` : new Date().toISOString()
        },
        location: [
          {
            location: {
              reference: `Location/soedarso-eg2-${(pt.room || 'eg2a').toLowerCase()}-bed-${pt.bed}`,
              display: `Ruang ${pt.room || 'Enggang Gading 2'} • Bed ${pt.bed}`
            },
            status: 'active',
            physicalType: {
              coding: [
                {
                  system: 'http://terminology.hl7.org/CodeSystem/location-physical-type',
                  code: 'bd',
                  display: 'Bed'
                }
              ]
            }
          }
        ],
        serviceProvider: {
          reference: 'Organization/soedarso-pontianak',
          display: 'RSUD Dr. Soedarso Pontianak'
        }
      };
    },

    /**
     * Konversi diagnosa ke HL7 FHIR v4 Condition Resource
     * @param {Object} pt - Objek pasien
     * @returns {Object} FHIR Condition Resource
     */
    toFhirCondition: function (pt) {
      if (!pt || !pt.diagnosis) return null;
      const mrNo = (pt.mrNo || '').trim();
      const patientRef = mrNo && mrNo !== '-' ? `Patient/pt-mrn-${mrNo.replace(/\D/g, '')}` : `Patient/pt-${encodeURIComponent(pt.name || 'anon')}`;
      const conditionId = `cond-${encodeURIComponent(mrNo || pt.name || 'dx')}`;

      return {
        resourceType: 'Condition',
        id: conditionId,
        meta: {
          profile: ['https://fhir.kemkes.go.id/r4/StructureDefinition/Condition'],
          lastUpdated: new Date().toISOString()
        },
        clinicalStatus: {
          coding: [
            {
              system: 'http://terminology.hl7.org/CodeSystem/condition-clinical',
              code: 'active',
              display: 'Active'
            }
          ]
        },
        verificationStatus: {
          coding: [
            {
              system: 'http://terminology.hl7.org/CodeSystem/condition-ver-status',
              code: 'confirmed',
              display: 'Confirmed'
            }
          ]
        },
        category: [
          {
            coding: [
              {
                system: 'http://terminology.hl7.org/CodeSystem/condition-category',
                code: 'encounter-diagnosis',
                display: 'Encounter Diagnosis'
              }
            ]
          }
        ],
        code: {
          text: pt.diagnosis
        },
        subject: {
          reference: patientRef,
          display: pt.name
        }
      };
    },

    /**
     * Ekstraksi parameter tanda vital dan hitung skor NEWS2 (National Early Warning Score 2)
     * Mengikuti pedoman Royal College of Physicians & Kemenkes RI
     * @param {Object} pt - Objek pasien dengan catatan klinis
     * @returns {Object} Objek hasil perhitungan NEWS2 & komponen vital signs
     */
    computeNews2: function (pt) {
      const notes = pt?.notes || {};
      const fullText = `${notes.pagi || ''} ${notes.sore || ''} ${notes.malam || ''} ${pt?.diagnosis || ''}`.toLowerCase();

      // Default fisiologis normal dewasa
      let sbp = 120;
      let hr = 78;
      let rr = 18;
      let temp = 36.6;
      let spo2 = 98;
      let onOxygen = false;
      let avpu = 'A'; // Alert

      // Ekstraksi Tekanan Darah (TD: xxx/yyy mmHg)
      const tdMatch = fullText.match(/(?:td|tensi)[\s:=]*(\d{2,3})\s*[\/|\\]\s*(\d{2,3})/i);
      if (tdMatch) {
        sbp = parseInt(tdMatch[1], 10);
      }

      // Ekstraksi Suhu (S: xx.x C)
      const tempMatch = fullText.match(/(?:suhu|temp|t)[\s:=]*(\d{2}(?:[.,]\d)?)\s*(?:c|°c)?/i);
      if (tempMatch) {
        temp = parseFloat(tempMatch[1].replace(',', '.'));
      }

      // Ekstraksi Laju Pernapasan / RR (RR: xx x/m)
      const rrMatch = fullText.match(/(?:rr|resp|pernapasan)[\s:=]*(\d{1,2})/i);
      if (rrMatch) {
        rr = parseInt(rrMatch[1], 10);
      } else if (fullText.includes('sesak')) {
        rr = 24; // Sesak klinis default
      }

      // Ekstraksi Nadi / Heart Rate (N: xx x/m)
      const hrMatch = fullText.match(/(?:nadi|hr|pulse)[\s:=]*(\d{2,3})/i);
      if (hrMatch) {
        hr = parseInt(hrMatch[1], 10);
      }

      // Deteksi Terapi Oksigen (O2 / nasal canul / nrm)
      if (fullText.includes('o2') || fullText.includes('oksigen') || fullText.includes('nasal') || fullText.includes('nrm')) {
        onOxygen = true;
      }

      // Deteksi Kesadaran (AVPU / GCS / Somnolen / Koma / Apatis)
      if (fullText.includes('sopor') || fullText.includes('koma') || fullText.includes('penurunan kesadaran')) {
        avpu = 'P/U';
      } else if (fullText.includes('somnolen') || fullText.includes('apatis')) {
        avpu = 'V';
      }

      // Kalkulasi Skor NEWS2 berdasarkan matriks Royal College of Physicians
      let score = 0;

      // 1. Respiration Rate (RR)
      if (rr <= 8) score += 3;
      else if (rr >= 9 && rr <= 11) score += 1;
      else if (rr >= 12 && rr <= 20) score += 0;
      else if (rr >= 21 && rr <= 24) score += 2;
      else if (rr >= 25) score += 3;

      // 2. SpO2 Scale 1 (tanpa hiperkapnia kronik)
      if (spo2 <= 91) score += 3;
      else if (spo2 >= 92 && spo2 <= 93) score += 2;
      else if (spo2 >= 94 && spo2 <= 95) score += 1;

      // 3. Suplemen Oksigen
      if (onOxygen) score += 2;

      // 4. Tekanan Darah Sistolik (SBP)
      if (sbp <= 90) score += 3;
      else if (sbp >= 91 && sbp <= 100) score += 2;
      else if (sbp >= 101 && sbp <= 110) score += 1;
      else if (sbp >= 111 && sbp <= 219) score += 0;
      else if (sbp >= 220) score += 3;

      // 5. Laju Nadi (Pulse)
      if (hr <= 40) score += 3;
      else if (hr >= 41 && hr <= 50) score += 1;
      else if (hr >= 51 && hr <= 90) score += 0;
      else if (hr >= 91 && hr <= 110) score += 1;
      else if (hr >= 111 && hr <= 130) score += 2;
      else if (hr >= 131) score += 3;

      // 6. Tingkat Kesadaran (AVPU)
      if (avpu !== 'A') score += 3;

      // 7. Suhu Tubuh
      if (temp <= 35.0) score += 3;
      else if (temp >= 35.1 && temp <= 36.0) score += 1;
      else if (temp >= 36.1 && temp <= 38.0) score += 0;
      else if (temp >= 38.1 && temp <= 39.0) score += 1;
      else if (temp >= 39.1) score += 2;

      // Tentukan Klasifikasi Risiko & Protokol Eskalasi Klinis
      let riskLevel = 'LOW';
      let riskLabel = 'Risiko Rendah';
      let riskClass = 'news-low';
      let clinicalResponse = 'Observasi rutin per shift (4-6 jam) oleh Perawat Pelaksana.';

      if (score >= 7) {
        riskLevel = 'HIGH';
        riskLabel = 'Risiko Tinggi (Gawat)';
        riskClass = 'news-high';
        clinicalResponse = '🚨 Segera lapor DPJP & Dokter Jaga. Pertimbangkan aktivasi Tim Reaksi Cepat / Alih Rawat HCU/ICU.';
      } else if (score >= 5 || (score === 3 && (sbp <= 90 || rr >= 25 || hr >= 131 || avpu !== 'A'))) {
        riskLevel = 'MEDIUM';
        riskLabel = 'Risiko Sedang';
        riskClass = 'news-medium';
        clinicalResponse = '⚠️ Lapor Dokter Jaga Ruangan dalam 30 menit. Naikkan frekuensi observasi menjadi tiap 1 jam.';
      }

      return {
        score: score,
        riskLevel: riskLevel,
        riskLabel: riskLabel,
        riskClass: riskClass,
        clinicalResponse: clinicalResponse,
        vitals: {
          sbp: sbp,
          hr: hr,
          rr: rr,
          temp: temp,
          spo2: spo2,
          onOxygen: onOxygen,
          avpu: avpu
        }
      };
    },

    /**
     * Membuat HL7 FHIR v4 Observation Resource untuk NEWS2 Bundle
     * @param {Object} pt - Pasien
     * @param {Object} newsData - Hasil perhitungan NEWS2
     * @returns {Object} FHIR Observation Resource
     */
    toFhirNewsObservation: function (pt, newsData) {
      if (!pt || !newsData) return null;
      const mrNo = (pt.mrNo || '').trim();
      const patientRef = mrNo && mrNo !== '-' ? `Patient/pt-mrn-${mrNo.replace(/\D/g, '')}` : `Patient/pt-${encodeURIComponent(pt.name || 'anon')}`;

      return {
        resourceType: 'Observation',
        id: `obs-news2-${encodeURIComponent(mrNo || pt.name || 'pt')}`,
        meta: {
          profile: ['https://fhir.kemkes.go.id/r4/StructureDefinition/Observation'],
          lastUpdated: new Date().toISOString()
        },
        status: 'final',
        category: [
          {
            coding: [
              {
                system: 'http://terminology.hl7.org/CodeSystem/observation-category',
                code: 'vital-signs',
                display: 'Vital Signs'
              }
            ]
          }
        ],
        code: {
          coding: [
            {
              system: 'http://loinc.org',
              code: '110405-8',
              display: 'National Early Warning Score 2 (NEWS2)'
            }
          ],
          text: 'NEWS2 Early Warning Score'
        },
        subject: {
          reference: patientRef,
          display: pt.name
        },
        effectiveDateTime: new Date().toISOString(),
        valueInteger: newsData.score,
        interpretation: [
          {
            coding: [
              {
                system: 'http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation',
                code: newsData.riskLevel === 'HIGH' ? 'AA' : (newsData.riskLevel === 'MEDIUM' ? 'A' : 'N'),
                display: newsData.riskLabel
              }
            ],
            text: newsData.clinicalResponse
          }
        ]
      };
    },

    /**
     * Membentuk HL7 FHIR v4 Bundle lengkap untuk satu pasien atau seluruh bangsal
     * @param {Array<Object>} patientList - Daftar pasien rawat inap
     * @param {string} dateStr - Tanggal sensus
     * @returns {Object} FHIR Transaction/Searchset Bundle
     */
    createWardFhirBundle: function (patientList, dateStr) {
      const entries = [];

      (patientList || []).forEach(pt => {
        if (!pt || pt.isEmpty) return;

        const fhirPt = this.toFhirPatient(pt);
        const fhirEnc = this.toFhirEncounter(pt, dateStr);
        const fhirCond = this.toFhirCondition(pt);
        const news = this.computeNews2(pt);
        const fhirObs = this.toFhirNewsObservation(pt, news);

        if (fhirPt) entries.push({ resource: fhirPt });
        if (fhirEnc) entries.push({ resource: fhirEnc });
        if (fhirCond) entries.push({ resource: fhirCond });
        if (fhirObs) entries.push({ resource: fhirObs });
      });

      return {
        resourceType: 'Bundle',
        id: `bundle-eg2-${(dateStr || 'today').replace(/-/g, '')}`,
        type: 'collection',
        meta: {
          lastUpdated: new Date().toISOString()
        },
        total: entries.length,
        entry: entries
      };
    }
  };

  // Export to global scope
  global.FHIRAdapter = FHIRAdapter;
})(typeof window !== 'undefined' ? window : this);
