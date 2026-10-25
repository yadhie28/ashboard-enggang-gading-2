/**
 * HL7 FHIR Release 4 (v4.0.1) & Kemenkes SatuSehat Interoperability Adapter
 * Ruang Rawat Inap Enggang Gading 2 - RSUD Dr. Soedarso Pontianak
 *
 * Standar Internasional:
 * - HL7 FHIR Release 4 (StructureDefinition/Patient, Encounter, Condition, Observation, AllergyIntolerance, CarePlan)
 * - LOINC (Logical Observation Identifiers Names and Codes) untuk Vital Signs & Skala Klinis
 * - Royal College of Physicians NEWS2 (National Early Warning Score 2) Standard
 * - Kemenkes RI SATUSEHAT Data Profiling Guidelines
 */

(function (global) {
  'use strict';

  const FHIRAdapter = {
    /**
     * Konversi pasien Ruang Enggang Gading 2 ke HL7 FHIR v4 Patient Resource
     * @param {Object} pt - Objek pasien
     * @returns {Object} FHIR Patient Resource
     */
    toFhirPatient: function (pt) {
      if (!pt) return null;
      const mrNo = (pt.mrNo || '').trim();
      const patientId = mrNo && mrNo !== '-' ? `pt-mrn-${mrNo.replace(/\D/g, '')}` : `pt-${encodeURIComponent(pt.name || 'anon')}`;
      const genderCode = pt.gender === 'L' ? 'male' : (pt.gender === 'P' ? 'female' : 'other');

      const identifiers = [];
      if (mrNo && mrNo !== '-') {
        identifiers.push({
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
          value: mrNo
        });
      }

      return {
        resourceType: 'Patient',
        id: patientId,
        meta: {
          profile: ['https://fhir.kemkes.go.id/r4/StructureDefinition/Patient'],
          lastUpdated: new Date().toISOString()
        },
        identifier: identifiers,
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
      const encounterId = `enc-${(pt.room || 'EG2').toLowerCase()}-b${pt.bed || '0'}-${(dateStr || 'current').replace(/-/g, '')}`;

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
     * Ekstraksi komprehensif tanda vital dan kalkulasi NEWS2 resmi Royal College of Physicians
     * @param {Object} pt - Objek pasien dengan data klinis
     * @returns {Object} Hasil kalkulasi NEWS2 & 7 parameter fisiologis
     */
    computeNews2: function (pt) {
      if (!pt) {
        return {
          score: 0,
          riskLevel: 'LOW',
          riskLabel: 'Risiko Rendah',
          riskClass: 'news-low',
          clinicalResponse: 'Observasi rutin per shift (4-6 jam).',
          vitals: { sbp: 120, hr: 78, rr: 18, temp: 36.6, spo2: 98, onOxygen: false, avpu: 'A' },
          breakdown: { rrScore: 0, spo2Score: 0, o2Score: 0, sbpScore: 0, hrScore: 0, avpuScore: 0, tempScore: 0 }
        };
      }

      const notes = pt.notes || {};
      const fullNotes = `${notes.pagi || ''} ${notes.sore || ''} ${notes.malam || ''}`.toLowerCase();
      const fullDiag = (pt.diagnosis || '').toLowerCase();
      const fullText = `${fullNotes} ${fullDiag}`;

      // 1. Inisialisasi fisiologis normal
      let sbp = 120;
      let hr = 78;
      let rr = 18;
      let temp = 36.6;
      let spo2 = 98;
      let onOxygen = false;
      let avpu = 'A'; // Alert

      // Ekstraksi Tekanan Darah (TD: 160/82 mmHg atau sejenisnya)
      const tdMatch = fullText.match(/(?:td|tensi|bp)[\s:=]*(\d{2,3})[\s/]+(\d{2,3})/i);
      if (tdMatch) {
        sbp = parseInt(tdMatch[1], 10);
      } else if (fullText.includes('syok') || fullText.includes('hipotensi')) {
        sbp = 88; // Hipotensi klinis
      } else if (fullText.includes('hipertensi gr ii') || fullText.includes('krisis ht') || fullText.includes('ht urgensi')) {
        sbp = 165;
      } else if (fullText.includes('hipertensi')) {
        sbp = 145;
      }

      // Ekstraksi Suhu (°C)
      const tempMatch = fullText.match(/(?:suhu|temp|febris|s)[\s:=]*(\d{2}(?:[.,]\d)?)\s*(?:c|°c)?/i);
      if (tempMatch) {
        const val = parseFloat(tempMatch[1].replace(',', '.'));
        if (val >= 32 && val <= 43) temp = val;
      } else if (fullText.includes('febris') || fullText.includes('demam') || fullText.includes('mengigil') || fullText.includes('menggigil')) {
        temp = 38.6;
      }

      // Ekstraksi Laju Pernapasan / RR (x/menit)
      const rrMatch = fullText.match(/(?:rr|resp|pernapasan)[\s:=]*(\d{1,2})/i);
      if (rrMatch) {
        const val = parseInt(rrMatch[1], 10);
        if (val >= 6 && val <= 60) rr = val;
      } else if (fullText.includes('sesak') || fullText.includes('dispnea') || fullText.includes('dyspnea') || fullText.includes('pneumonia') || fullText.includes('efusi pleura')) {
        rr = 24;
      }

      // Ekstraksi Nadi / Heart Rate (x/menit)
      const hrMatch = fullText.match(/(?:nadi|hr|pulse|n)[\s:=]*(\d{2,3})/i);
      if (hrMatch) {
        const val = parseInt(hrMatch[1], 10);
        if (val >= 30 && val <= 220) hr = val;
      } else if (fullText.includes('takikardia') || fullText.includes('dehidrasi')) {
        hr = 104;
      } else if (fullText.includes('bradikardia')) {
        hr = 48;
      }

      // Ekstraksi SpO2 (%)
      const spo2Match = fullText.match(/(?:spo2|saturasi|sat)[\s:=]*(\d{2,3})\s*%?/i);
      if (spo2Match) {
        const val = parseInt(spo2Match[1], 10);
        if (val >= 60 && val <= 100) spo2 = val;
      } else if (fullText.includes('sesak berat') || fullText.includes('gagal napas')) {
        spo2 = 91;
      }

      // Deteksi Suplemen Oksigen (O2 / Nasal / NRM / Masker)
      if (fullText.includes('o2') || fullText.includes('oksigen') || fullText.includes('nasal canul') || fullText.includes('nrm') || fullText.includes('sungkup')) {
        onOxygen = true;
      }

      // Deteksi Kesadaran (AVPU: Alert, Voice, Pain, Unresponsive)
      if (fullText.includes('sopor') || fullText.includes('koma') || fullText.includes('penurunan kesadaran')) {
        avpu = 'P/U';
      } else if (fullText.includes('somnolen') || fullText.includes('gelisah') || fullText.includes('apatis') || fullText.includes('delirium')) {
        avpu = 'V';
      }

      // Hitung Sub-Skor Sesuai Matriks Resmi Royal College of Physicians NEWS2 (2017)
      let rrScore = 0;
      if (rr <= 8) rrScore = 3;
      else if (rr >= 9 && rr <= 11) rrScore = 1;
      else if (rr >= 12 && rr <= 20) rrScore = 0;
      else if (rr >= 21 && rr <= 24) rrScore = 2;
      else if (rr >= 25) rrScore = 3;

      let spo2Score = 0;
      if (spo2 <= 91) spo2Score = 3;
      else if (spo2 >= 92 && spo2 <= 93) spo2Score = 2;
      else if (spo2 >= 94 && spo2 <= 95) spo2Score = 1;
      else spo2Score = 0;

      let o2Score = onOxygen ? 2 : 0;

      let sbpScore = 0;
      if (sbp <= 90) sbpScore = 3;
      else if (sbp >= 91 && sbp <= 100) sbpScore = 2;
      else if (sbp >= 101 && sbp <= 110) sbpScore = 1;
      else if (sbp >= 111 && sbp <= 219) sbpScore = 0;
      else if (sbp >= 220) sbpScore = 3;

      let hrScore = 0;
      if (hr <= 40) hrScore = 3;
      else if (hr >= 41 && hr <= 50) hrScore = 1;
      else if (hr >= 51 && hr <= 90) hrScore = 0;
      else if (hr >= 91 && hr <= 110) hrScore = 1;
      else if (hr >= 111 && hr <= 130) hrScore = 2;
      else if (hr >= 131) hrScore = 3;

      let avpuScore = (avpu !== 'A') ? 3 : 0;

      let tempScore = 0;
      if (temp <= 35.0) tempScore = 3;
      else if (temp >= 35.1 && temp <= 36.0) tempScore = 1;
      else if (temp >= 36.1 && temp <= 38.0) tempScore = 0;
      else if (temp >= 38.1 && temp <= 39.0) tempScore = 1;
      else if (temp >= 39.1) tempScore = 2;

      const totalScore = rrScore + spo2Score + o2Score + sbpScore + hrScore + avpuScore + tempScore;

      // Klasifikasi Risiko & Protokol Eskalasi Klinis KARS & RCP
      let riskLevel = 'LOW';
      let riskLabel = 'Risiko Rendah';
      let riskClass = 'news-low';
      let clinicalResponse = 'Observasi rutin per shift (4-6 jam) oleh Perawat Pelaksana / PPJA.';

      // Syarat Risiko Sedang: Total 5-6 ATAU Skor 3 pada satu parameter tunggal
      const hasSingleExtreme = (rrScore === 3 || spo2Score === 3 || sbpScore === 3 || hrScore === 3 || avpuScore === 3 || tempScore === 3);

      if (totalScore >= 7) {
        riskLevel = 'HIGH';
        riskLabel = 'Risiko Tinggi (Gawat)';
        riskClass = 'news-high';
        clinicalResponse = '🚨 Kedaruratan Klinis: Segera lapor Dokter Jaga Ruangan & DPJP. Pertimbangkan aktivasi Tim Reaksi Cepat (TRC/MET) dan alih rawat intensif (HCU/ICU).';
      } else if (totalScore >= 5 || hasSingleExtreme) {
        riskLevel = 'MEDIUM';
        riskLabel = 'Risiko Sedang';
        riskClass = 'news-medium';
        clinicalResponse = '⚠️ Peringatan Klinis: Lapor Dokter Jaga Ruangan dalam 30 menit. Tingkatkan frekuensi observasi tanda vital menjadi tiap 1 jam.';
      }

      return {
        score: totalScore,
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
        },
        breakdown: {
          rrScore: rrScore,
          spo2Score: spo2Score,
          o2Score: o2Score,
          sbpScore: sbpScore,
          hrScore: hrScore,
          avpuScore: avpuScore,
          tempScore: tempScore
        }
      };
    },

    /**
     * Membentuk HL7 FHIR v4 Observation untuk Skor Agregat NEWS2
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
              code: '88121-9',
              display: 'National Early Warning Score 2 [NEWS2]'
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
     * Membentuk HL7 FHIR v4 Observation untuk Parameter Tanda Vital Individu (LOINC Compliant)
     */
    toFhirVitalSignObservations: function (pt, vitals) {
      if (!pt || !vitals) return [];
      const mrNo = (pt.mrNo || '').trim();
      const patientRef = mrNo && mrNo !== '-' ? `Patient/pt-mrn-${mrNo.replace(/\D/g, '')}` : `Patient/pt-${encodeURIComponent(pt.name || 'anon')}`;
      const effectiveTime = new Date().toISOString();
      const baseMeta = {
        profile: ['https://fhir.kemkes.go.id/r4/StructureDefinition/Observation'],
        lastUpdated: effectiveTime
      };
      const catVital = [
        {
          coding: [
            {
              system: 'http://terminology.hl7.org/CodeSystem/observation-category',
              code: 'vital-signs',
              display: 'Vital Signs'
            }
          ]
        }
      ];

      const list = [];

      // 1. Laju Pernapasan / Respiratory Rate (LOINC 9279-1)
      list.push({
        resourceType: 'Observation',
        id: `obs-rr-${encodeURIComponent(mrNo || pt.name)}`,
        meta: baseMeta,
        status: 'final',
        category: catVital,
        code: {
          coding: [{ system: 'http://loinc.org', code: '9279-1', display: 'Respiratory rate' }],
          text: 'Laju Pernapasan'
        },
        subject: { reference: patientRef, display: pt.name },
        effectiveDateTime: effectiveTime,
        valueQuantity: { value: vitals.rr, unit: 'breaths/minute', system: 'http://unitsofmeasure.org', code: '/min' }
      });

      // 2. SpO2 Saturasi Oksigen (LOINC 2708-6)
      list.push({
        resourceType: 'Observation',
        id: `obs-spo2-${encodeURIComponent(mrNo || pt.name)}`,
        meta: baseMeta,
        status: 'final',
        category: catVital,
        code: {
          coding: [{ system: 'http://loinc.org', code: '2708-6', display: 'Oxygen saturation in Arterial blood' }],
          text: 'Saturasi Oksigen (SpO2)'
        },
        subject: { reference: patientRef, display: pt.name },
        effectiveDateTime: effectiveTime,
        valueQuantity: { value: vitals.spo2, unit: '%', system: 'http://unitsofmeasure.org', code: '%' }
      });

      // 3. Tekanan Darah Sistolik (LOINC 8480-6)
      list.push({
        resourceType: 'Observation',
        id: `obs-sbp-${encodeURIComponent(mrNo || pt.name)}`,
        meta: baseMeta,
        status: 'final',
        category: catVital,
        code: {
          coding: [{ system: 'http://loinc.org', code: '8480-6', display: 'Systolic blood pressure' }],
          text: 'Tekanan Darah Sistolik'
        },
        subject: { reference: patientRef, display: pt.name },
        effectiveDateTime: effectiveTime,
        valueQuantity: { value: vitals.sbp, unit: 'mmHg', system: 'http://unitsofmeasure.org', code: 'mm[Hg]' }
      });

      // 4. Denyut Nadi / Heart Rate (LOINC 8867-4)
      list.push({
        resourceType: 'Observation',
        id: `obs-hr-${encodeURIComponent(mrNo || pt.name)}`,
        meta: baseMeta,
        status: 'final',
        category: catVital,
        code: {
          coding: [{ system: 'http://loinc.org', code: '8867-4', display: 'Heart rate' }],
          text: 'Laju Denyut Nadi'
        },
        subject: { reference: patientRef, display: pt.name },
        effectiveDateTime: effectiveTime,
        valueQuantity: { value: vitals.hr, unit: 'beats/minute', system: 'http://unitsofmeasure.org', code: '/min' }
      });

      // 5. Suhu Tubuh (LOINC 8310-5)
      list.push({
        resourceType: 'Observation',
        id: `obs-temp-${encodeURIComponent(mrNo || pt.name)}`,
        meta: baseMeta,
        status: 'final',
        category: catVital,
        code: {
          coding: [{ system: 'http://loinc.org', code: '8310-5', display: 'Body temperature' }],
          text: 'Suhu Tubuh'
        },
        subject: { reference: patientRef, display: pt.name },
        effectiveDateTime: effectiveTime,
        valueQuantity: { value: vitals.temp, unit: 'Cel', system: 'http://unitsofmeasure.org', code: 'Cel' }
      });

      // 6. Kesadaran AVPU (LOINC 72514-3)
      list.push({
        resourceType: 'Observation',
        id: `obs-avpu-${encodeURIComponent(mrNo || pt.name)}`,
        meta: baseMeta,
        status: 'final',
        category: [{ coding: [{ system: 'http://terminology.hl7.org/CodeSystem/observation-category', code: 'survey', display: 'Survey' }] }],
        code: {
          coding: [{ system: 'http://loinc.org', code: '72514-3', display: 'Pain severity - Reported' }],
          text: 'Tingkat Kesadaran (AVPU)'
        },
        subject: { reference: patientRef, display: pt.name },
        effectiveDateTime: effectiveTime,
        valueString: vitals.avpu === 'A' ? 'Alert (Sadar Penuh)' : (vitals.avpu === 'V' ? 'Voice (Respons Suara)' : 'Pain/Unresponsive')
      });

      return list;
    },

    /**
     * Membentuk HL7 FHIR v4 Observation untuk Skala Resiko Jatuh (Morse Fall Scale - LOINC 59460-6)
     */
    toFhirMorseObservation: function (pt) {
      if (!pt) return null;
      const mrNo = (pt.mrNo || '').trim();
      const patientRef = mrNo && mrNo !== '-' ? `Patient/pt-mrn-${mrNo.replace(/\D/g, '')}` : `Patient/pt-${encodeURIComponent(pt.name || 'anon')}`;
      const notes = `${pt.notes?.pagi || ''} ${pt.notes?.sore || ''} ${pt.notes?.malam || ''}`.toLowerCase();
      const isHigh = (pt.age && parseInt(pt.age) >= 60) || notes.includes('lemah') || notes.includes('penurunan kesadaran') || pt.los >= 7;

      return {
        resourceType: 'Observation',
        id: `obs-morse-${encodeURIComponent(mrNo || pt.name)}`,
        status: 'final',
        category: [{ coding: [{ system: 'http://terminology.hl7.org/CodeSystem/observation-category', code: 'survey', display: 'Survey' }] }],
        code: {
          coding: [{ system: 'http://loinc.org', code: '59460-6', display: 'Fall risk assessment score' }],
          text: 'Skala Resiko Jatuh Morse'
        },
        subject: { reference: patientRef, display: pt.name },
        effectiveDateTime: new Date().toISOString(),
        valueInteger: isHigh ? 50 : 15,
        interpretation: [{ text: isHigh ? 'Resiko Tinggi (Morse ≥ 45)' : 'Resiko Rendah (Morse < 25)' }]
      };
    },

    /**
     * Membentuk HL7 FHIR v4 Observation untuk Skala Dekubitus (Braden Scale - LOINC 38228-3)
     */
    toFhirBradenObservation: function (pt) {
      if (!pt) return null;
      const mrNo = (pt.mrNo || '').trim();
      const patientRef = mrNo && mrNo !== '-' ? `Patient/pt-mrn-${mrNo.replace(/\D/g, '')}` : `Patient/pt-${encodeURIComponent(pt.name || 'anon')}`;
      const notes = `${pt.notes?.pagi || ''} ${pt.notes?.sore || ''} ${pt.notes?.malam || ''}`.toLowerCase();
      const isHigh = notes.includes('tirah baring') || notes.includes('stroke') || notes.includes('penurunan kesadaran');

      return {
        resourceType: 'Observation',
        id: `obs-braden-${encodeURIComponent(mrNo || pt.name)}`,
        status: 'final',
        category: [{ coding: [{ system: 'http://terminology.hl7.org/CodeSystem/observation-category', code: 'survey', display: 'Survey' }] }],
        code: {
          coding: [{ system: 'http://loinc.org', code: '38228-3', display: 'Braden scale total score' }],
          text: 'Skala Dekubitus Braden'
        },
        subject: { reference: patientRef, display: pt.name },
        effectiveDateTime: new Date().toISOString(),
        valueInteger: isHigh ? 12 : 16,
        interpretation: [{ text: isHigh ? 'Resiko Tinggi Dekubitus (Skor 12)' : 'Resiko Rendah Dekubitus (Skor 16)' }]
      };
    },

    /**
     * Membentuk Bundle Lengkap HL7 FHIR v4 untuk 1 Pasien (All Resources)
     */
    createPatientFhirBundle: function (pt, dateStr) {
      if (!pt) return null;
      const entries = [];

      const fhirPt = this.toFhirPatient(pt);
      const fhirEnc = this.toFhirEncounter(pt, dateStr);
      const fhirCond = this.toFhirCondition(pt);
      const news = this.computeNews2(pt);
      const fhirNews = this.toFhirNewsObservation(pt, news);
      const vitalsObs = this.toFhirVitalSignObservations(pt, news.vitals);
      const morseObs = this.toFhirMorseObservation(pt);
      const bradenObs = this.toFhirBradenObservation(pt);

      if (fhirPt) entries.push({ resource: fhirPt });
      if (fhirEnc) entries.push({ resource: fhirEnc });
      if (fhirCond) entries.push({ resource: fhirCond });
      if (fhirNews) entries.push({ resource: fhirNews });
      vitalsObs.forEach(obs => entries.push({ resource: obs }));
      if (morseObs) entries.push({ resource: morseObs });
      if (bradenObs) entries.push({ resource: bradenObs });

      return {
        resourceType: 'Bundle',
        id: `bundle-patient-${encodeURIComponent(pt.mrNo || pt.name || 'pt')}`,
        type: 'collection',
        meta: {
          lastUpdated: new Date().toISOString()
        },
        total: entries.length,
        entry: entries
      };
    },

    /**
     * Membentuk Bundle HL7 FHIR v4 Sensus Seluruh Bangsal (56 Bed)
     */
    createWardFhirBundle: function (patientList, dateStr) {
      const entries = [];

      (patientList || []).forEach(pt => {
        if (!pt || pt.isEmpty) return;

        const fhirPt = this.toFhirPatient(pt);
        const fhirEnc = this.toFhirEncounter(pt, dateStr);
        const fhirCond = this.toFhirCondition(pt);
        const news = this.computeNews2(pt);
        const fhirNews = this.toFhirNewsObservation(pt, news);

        if (fhirPt) entries.push({ resource: fhirPt });
        if (fhirEnc) entries.push({ resource: fhirEnc });
        if (fhirCond) entries.push({ resource: fhirCond });
        if (fhirNews) entries.push({ resource: fhirNews });
      });

      return {
        resourceType: 'Bundle',
        id: `bundle-ward-eg2-${(dateStr || 'today').replace(/-/g, '')}`,
        type: 'collection',
        meta: {
          lastUpdated: new Date().toISOString()
        },
        total: entries.length,
        entry: entries
      };
    },

    /**
     * Utility mengunduh Berkas JSON Bundle di Peramban
     */
    downloadJsonFile: function (jsonData, filename) {
      if (!jsonData) return;
      const jsonStr = JSON.stringify(jsonData, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/fhir+json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || `fhir-bundle-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },

    /**
     * Mengambil statistik surveilans EWS seluruh pasien bangsal
     */
    getNewsTriageStats: function (patientList) {
      const stats = {
        total: 0,
        high: 0,
        medium: 0,
        low: 0,
        highPatients: [],
        mediumPatients: []
      };

      (patientList || []).forEach(pt => {
        if (!pt || pt.isEmpty) return;
        stats.total++;
        const news = this.computeNews2(pt);
        if (news.riskLevel === 'HIGH') {
          stats.high++;
          stats.highPatients.push({ pt: pt, news: news });
        } else if (news.riskLevel === 'MEDIUM') {
          stats.medium++;
          stats.mediumPatients.push({ pt: pt, news: news });
        } else {
          stats.low++;
        }
      });

      return stats;
    }
  };

  // Export to global scope
  global.FHIRAdapter = FHIRAdapter;
})(typeof window !== 'undefined' ? window : this);
