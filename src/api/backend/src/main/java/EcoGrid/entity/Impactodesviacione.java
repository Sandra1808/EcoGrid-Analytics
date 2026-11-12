package EcoGrid.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.math.BigDecimal;

@Entity
@Table(name = "IMPACTODESVIACIONES")
public class Impactodesviacione {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDIMPACTO", nullable = false)
    private Long id;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDTIEMPO", nullable = false)
    private Tiempohorario idtiempo;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDPREDICCION")
    private Prediccionesdemanda idprediccion;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDCCAA", nullable = false)
    private Comunidadautonoma idccaa;

    @Column(name = "DEMANDAREALMW", precision = 12, scale = 4)
    private BigDecimal demandarealmw;

    @Column(name = "DEMANDAPREDICHAMW", precision = 12, scale = 4)
    private BigDecimal demandapredichamw;

    @Column(name = "DESVIACIONMW", precision = 12, scale = 4)
    private BigDecimal desviacionmw;

    @Column(name = "PRECIOOMIEEURMWH", precision = 10, scale = 4)
    private BigDecimal precioomieeurmwh;

    @Column(name = "COSTEDESVIOESTIMADOEUR", precision = 14, scale = 4)
    private BigDecimal costedesvioestimadoeur;

    @Size(max = 50)
    @Column(name = "NIVELALERTA", length = 50)
    private String nivelalerta;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Tiempohorario getIdtiempo() {
        return idtiempo;
    }

    public void setIdtiempo(Tiempohorario idtiempo) {
        this.idtiempo = idtiempo;
    }

    public Prediccionesdemanda getIdprediccion() {
        return idprediccion;
    }

    public void setIdprediccion(Prediccionesdemanda idprediccion) {
        this.idprediccion = idprediccion;
    }

    public Comunidadautonoma getIdccaa() {
        return idccaa;
    }

    public void setIdccaa(Comunidadautonoma idccaa) {
        this.idccaa = idccaa;
    }

    public BigDecimal getDemandarealmw() {
        return demandarealmw;
    }

    public void setDemandarealmw(BigDecimal demandarealmw) {
        this.demandarealmw = demandarealmw;
    }

    public BigDecimal getDemandapredichamw() {
        return demandapredichamw;
    }

    public void setDemandapredichamw(BigDecimal demandapredichamw) {
        this.demandapredichamw = demandapredichamw;
    }

    public BigDecimal getDesviacionmw() {
        return desviacionmw;
    }

    public void setDesviacionmw(BigDecimal desviacionmw) {
        this.desviacionmw = desviacionmw;
    }

    public BigDecimal getPrecioomieeurmwh() {
        return precioomieeurmwh;
    }

    public void setPrecioomieeurmwh(BigDecimal precioomieeurmwh) {
        this.precioomieeurmwh = precioomieeurmwh;
    }

    public BigDecimal getCostedesvioestimadoeur() {
        return costedesvioestimadoeur;
    }

    public void setCostedesvioestimadoeur(BigDecimal costedesvioestimadoeur) {
        this.costedesvioestimadoeur = costedesvioestimadoeur;
    }

    public String getNivelalerta() {
        return nivelalerta;
    }

    public void setNivelalerta(String nivelalerta) {
        this.nivelalerta = nivelalerta;
    }

}